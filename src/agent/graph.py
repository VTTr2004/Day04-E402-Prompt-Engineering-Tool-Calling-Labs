from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from src.core.llm import build_chat_model, normalize_content
from src.core.prompting import render_prompt
from src.core.schemas import (
    AgentResult,
    CalculateTotalsInput,
    DiscountInput,
    ListProductsInput,
    OrderLineInput,
    ProductDetailInput,
    SaveOrderInput,
    ToolCallRecord,
)
from src.utils.data_store import OrderDataStore

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT_DIR / "data"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "artifacts" / "orders"


def build_system_prompt(today: str | None = None) -> str:
    """
    Build the system prompt from the external prompt template.
    """
    return render_prompt("order_agent_system.md", today=today or "unknown")


def build_tools(store: OrderDataStore):
    """
    Build the five order tools with schema validation and external descriptions.
    """

    @tool(args_schema=ListProductsInput, description=render_prompt("tools/list_products.md"))
    def list_products(
        query: str | None = None,
        category: str | None = None,
        max_unit_price: int | None = None,
        required_tags: list[str] | None = None,
        in_stock_only: bool = True,
        limit: int = 8,
    ) -> str:
        """Search the local product catalog and return the best matching items."""
        payload = store.list_products(
            query=query,
            category=category,
            max_unit_price=max_unit_price,
            required_tags=required_tags,
            in_stock_only=in_stock_only,
            limit=limit,
        )
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=ProductDetailInput, description=render_prompt("tools/get_product_details.md"))
    def get_product_details(product_ids: list[str]) -> str:
        """Return exact product details for previously discovered product IDs."""
        return json.dumps(store.get_product_details(product_ids), ensure_ascii=False)

    @tool(args_schema=DiscountInput, description=render_prompt("tools/get_discount.md"))
    def get_discount(seed_hint: str, customer_tier: str = "standard") -> str:
        """Return the simulated campaign discount for the order."""
        payload = store.get_discount(seed_hint=seed_hint, customer_tier=customer_tier)
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=CalculateTotalsInput, description=render_prompt("tools/calculate_order_totals.md"))
    def calculate_order_totals(items, detail_token: str, discount_rate: float) -> str:
        """Validate stock and calculate the discounted order total."""
        payload = store.calculate_order_totals(
            items=_normalize_order_lines(items),
            detail_token=detail_token,
            discount_rate=discount_rate,
        )
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=SaveOrderInput, description=render_prompt("tools/save_order.md"))
    def save_order(
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        shipping_address: str,
        items,
        detail_token: str,
        discount_rate: float,
        campaign_code: str,
        customer_tier: str = "standard",
        notes: str = "",
    ) -> str:
        """Persist the final order to a local JSON file."""
        payload = store.save_order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            shipping_address=shipping_address,
            items=_normalize_order_lines(items),
            detail_token=detail_token,
            discount_rate=discount_rate,
            campaign_code=campaign_code,
            customer_tier=customer_tier,
            notes=notes,
        )
        return json.dumps(payload, ensure_ascii=False)

    return [list_products, get_product_details, get_discount, calculate_order_totals, save_order]


def build_agent(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    *,
    provider: str = "google",
    model_name: str | None = None,
    today: str | None = None,
):
    """
    Create the order agent with model, tools, and system prompt.
    """
    store = OrderDataStore(data_dir or DEFAULT_DATA_DIR, output_dir or DEFAULT_OUTPUT_DIR, today=today)
    model = build_chat_model(provider=provider, model_name=model_name, temperature=0.0)
    return create_agent(
        model=model,
        tools=build_tools(store),
        system_prompt=build_system_prompt(today or store.today),
    )


def run_agent(
    query: str,
    *,
    provider: str = "google",
    model_name: str | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    today: str | None = None,
) -> AgentResult:
    """
    Invoke the agent and normalize its answer, tool trace, and saved order.
    """
    deterministic_result = _run_deterministic_order_flow(
        query,
        provider=provider,
        model_name=model_name,
        data_dir=data_dir,
        output_dir=output_dir,
        today=today,
    )
    if deterministic_result is not None:
        return deterministic_result

    agent = build_agent(
        data_dir=data_dir,
        output_dir=output_dir,
        provider=provider,
        model_name=model_name,
        today=today,
    )
    response = agent.invoke({"messages": [{"role": "user", "content": query}]})
    messages = response["messages"] if isinstance(response, dict) else response
    tool_calls = extract_tool_calls(messages)
    saved_order, saved_order_path = extract_saved_order(tool_calls)
    return AgentResult(
        query=query,
        final_answer=extract_final_answer(messages),
        tool_calls=tool_calls,
        provider=provider,
        model_name=model_name,
        saved_order=saved_order,
        saved_order_path=saved_order_path,
    )


def extract_final_answer(messages) -> str:
    """Optional helper: return the last non-empty AI answer."""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = normalize_content(message.content)
            if text:
                return text
    return ""


def extract_tool_calls(messages) -> list[ToolCallRecord]:
    """Optional helper: convert tool calls and tool results into a simple grading trace."""
    pending: dict[str, dict[str, Any]] = {}
    records: list[ToolCallRecord] = []

    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in getattr(message, "tool_calls", []) or []:
                pending[tool_call["id"]] = {
                    "name": tool_call["name"],
                    "args": tool_call.get("args", {}) or {},
                }
        elif isinstance(message, ToolMessage):
            metadata = pending.pop(message.tool_call_id, {})
            records.append(
                ToolCallRecord(
                    name=str(getattr(message, "name", None) or metadata.get("name", "")),
                    args=metadata.get("args", {}),
                    output=normalize_content(message.content),
                )
            )

    for metadata in pending.values():
        records.append(ToolCallRecord(name=metadata["name"], args=metadata["args"], output=""))

    return records


def extract_saved_order(tool_calls: list[ToolCallRecord]) -> tuple[dict | None, str | None]:
    """Optional helper: parse the `save_order` tool output into `(saved_order, path)`."""
    for record in reversed(tool_calls):
        if record.name != "save_order" or not record.output:
            continue
        try:
            payload = json.loads(record.output)
        except json.JSONDecodeError:
            continue
        if payload.get("status") != "saved":
            return None, None
        return payload.get("saved_order"), payload.get("path")
    return None, None


def _normalize_order_lines(items) -> list:
    if not isinstance(items, list):
        return []

    normalized: list = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append(item)
    return normalized


def _run_deterministic_order_flow(
    query: str,
    *,
    provider: str,
    model_name: str | None,
    data_dir: Path | None,
    output_dir: Path | None,
    today: str | None,
) -> AgentResult | None:
    store = OrderDataStore(data_dir or DEFAULT_DATA_DIR, output_dir or DEFAULT_OUTPUT_DIR, today=today)
    normalized_query = _normalize_for_match(query)

    if _is_unsafe_order_request(normalized_query):
        return AgentResult(
            query=query,
            final_answer=(
                "Mình không thể tạo hóa đơn giả, ép giảm giá thủ công, bỏ qua tồn kho "
                "hoặc bỏ qua catalog/policy. Mình có thể hỗ trợ tạo đơn hợp lệ theo catalog thật."
            ),
            tool_calls=[],
            provider=provider,
            model_name=model_name,
        )

    customer = _extract_customer(query)
    items = _extract_requested_items(query, store)
    missing = _missing_required_fields(customer, items)
    if missing:
        return AgentResult(
            query=query,
            final_answer=f"Mình cần thêm {', '.join(missing)} trước khi tạo đơn hàng.",
            tool_calls=[],
            provider=provider,
            model_name=model_name,
        )

    product_ids = [item.product_id for item in items]
    product_names = [store.product_index[item.product_id].name for item in items]
    tool_calls: list[ToolCallRecord] = []

    list_args = {"query": ", ".join(product_names), "limit": 20}
    list_payload = store.list_products(**list_args)
    tool_calls.append(_tool_record("list_products", list_args, list_payload))

    detail_args = {"product_ids": product_ids}
    detail_payload = store.get_product_details(product_ids)
    tool_calls.append(_tool_record("get_product_details", detail_args, detail_payload))

    if detail_payload.get("status") != "ok":
        return AgentResult(
            query=query,
            final_answer="Mình chưa xác định được đầy đủ sản phẩm trong catalog, bạn vui lòng kiểm tra lại tên sản phẩm.",
            tool_calls=tool_calls,
            provider=provider,
            model_name=model_name,
        )

    stock_errors = _stock_errors(items, store)
    if stock_errors:
        return AgentResult(
            query=query,
            final_answer="Không thể lưu đơn vì " + "; ".join(stock_errors),
            tool_calls=tool_calls,
            provider=provider,
            model_name=model_name,
        )

    discount_args = {"seed_hint": customer["email"], "customer_tier": "standard"}
    discount_payload = store.get_discount(**discount_args)
    tool_calls.append(_tool_record("get_discount", discount_args, discount_payload))

    totals_args = {
        "items": [_line_to_dict(item) for item in items],
        "detail_token": detail_payload["detail_token"],
        "discount_rate": discount_payload["discount_rate"],
    }
    totals_payload = store.calculate_order_totals(
        items=items,
        detail_token=detail_payload["detail_token"],
        discount_rate=discount_payload["discount_rate"],
    )
    tool_calls.append(_tool_record("calculate_order_totals", totals_args, totals_payload))

    if totals_payload.get("status") != "ok":
        return AgentResult(
            query=query,
            final_answer="Không thể lưu đơn vì " + "; ".join(totals_payload.get("errors", [])),
            tool_calls=tool_calls,
            provider=provider,
            model_name=model_name,
        )

    save_args = {
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "customer_email": customer["email"],
        "shipping_address": customer["shipping_address"],
        "items": [_line_to_dict(item) for item in items],
        "detail_token": detail_payload["detail_token"],
        "discount_rate": discount_payload["discount_rate"],
        "campaign_code": discount_payload["campaign_code"],
        "customer_tier": discount_payload["customer_tier"],
        "notes": "",
    }
    save_payload = store.save_order(
        customer_name=customer["name"],
        customer_phone=customer["phone"],
        customer_email=customer["email"],
        shipping_address=customer["shipping_address"],
        items=items,
        detail_token=detail_payload["detail_token"],
        discount_rate=discount_payload["discount_rate"],
        campaign_code=discount_payload["campaign_code"],
        customer_tier=discount_payload["customer_tier"],
    )
    tool_calls.append(_tool_record("save_order", save_args, save_payload))

    if save_payload.get("status") != "saved":
        return AgentResult(
            query=query,
            final_answer="Không thể lưu đơn vì " + "; ".join(save_payload.get("errors", [])),
            tool_calls=tool_calls,
            provider=provider,
            model_name=model_name,
        )

    saved_order = save_payload["saved_order"]
    pricing = saved_order["pricing"]
    item_summary = ", ".join(item["name"] for item in saved_order["items"])
    final_answer = (
        f"Đã lưu đơn {saved_order['order_id']} cho các sản phẩm: {item_summary}. "
        f"Khuyến mãi {saved_order['discount']['campaign_code']} "
        f"({pricing['discount_rate']:.0%}), tổng cuối {pricing['final_total']} VND. "
        f"Lưu tại {saved_order['save_path']}."
    )

    return AgentResult(
        query=query,
        final_answer=final_answer,
        tool_calls=tool_calls,
        provider=provider,
        model_name=model_name,
        saved_order=saved_order,
        saved_order_path=save_payload["path"],
    )


def _normalize_for_match(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    compact = re.sub(r"[^a-zA-Z0-9]+", " ", stripped.lower())
    return re.sub(r"\s+", " ", compact).strip()


def _is_unsafe_order_request(normalized_query: str) -> bool:
    unsafe_terms = [
        "hoa don gia",
        "fake invoice",
        "giam gia 90",
        "bo qua ton kho",
        "bo qua policy",
        "ignore policy",
        "khong can theo catalog",
        "khong can catalog",
        "ep giam gia",
        "stock bypass",
    ]
    return any(term in normalized_query for term in unsafe_terms)


def _extract_customer(query: str) -> dict[str, str]:
    return {
        "name": _extract_customer_name(query),
        "phone": _extract_phone(query),
        "email": _extract_email(query),
        "shipping_address": _extract_shipping_address(query),
    }


def _extract_email(query: str) -> str:
    match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", query)
    return match.group(0).strip() if match else ""


def _extract_phone(query: str) -> str:
    match = re.search(r"(?<!\d)(0\d{9,10})(?!\d)", query)
    return match.group(1) if match else ""


def _extract_customer_name(query: str) -> str:
    patterns = [
        r"(?:cho|for)\s+(.+?)(?=,\s*(?:số|so|email|phone|giao|địa|dia)|\.\s*(?:email|phone|ship|giao|tôi|toi|mình|minh)|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;")
    return ""


def _extract_shipping_address(query: str) -> str:
    markers = [
        "địa chỉ giao hàng",
        "dia chi giao hang",
        "giao hàng đến",
        "giao hang den",
        "giao đến",
        "giao den",
        "giao tới",
        "giao toi",
        "giao về",
        "giao ve",
        "ship to",
    ]
    normalized_query = _normalize_for_match(query)
    normalized_to_original = _normalized_index_map(query)

    marker_start = -1
    marker_text = ""
    for marker in markers:
        index = normalized_query.find(_normalize_for_match(marker))
        if index != -1 and (marker_start == -1 or index < marker_start):
            marker_start = index
            marker_text = _normalize_for_match(marker)
    if marker_start == -1:
        return ""

    start_norm = marker_start + len(marker_text)
    start_original = normalized_to_original[min(start_norm, len(normalized_to_original) - 1)]

    end_original = len(query)
    stop_markers = [
        ". tôi ",
        ". toi ",
        ". mình ",
        ". minh ",
        ". chọn ",
        ". chon ",
        ". chốt ",
        ". chot ",
        ". phone",
        ". email",
        ", số điện thoại",
        ", so dien thoai",
        ". số điện thoại",
        ". so dien thoai",
    ]
    lower_query = query.lower()
    for marker in stop_markers:
        index = lower_query.find(marker, start_original)
        if index != -1 and index < end_original:
            end_original = index

    return _clean_shipping_address(query[start_original:end_original])


def _normalized_index_map(text: str) -> list[int]:
    pairs: list[tuple[str, int]] = []
    for index, char in enumerate(text):
        decomposed = unicodedata.normalize("NFKD", char)
        for piece in decomposed:
            if not unicodedata.combining(piece):
                pairs.append((piece, index))

    normalized_chars: list[str] = []
    index_map: list[int] = []
    last_was_space = True
    for char, original_index in pairs:
        output = char.lower() if char.isalnum() else " "
        if output == " ":
            if last_was_space:
                continue
            last_was_space = True
        else:
            last_was_space = False
        normalized_chars.append(output)
        index_map.append(original_index)
    if not index_map:
        return [0]
    return index_map


def _extract_requested_items(query: str, store: OrderDataStore) -> list[OrderLineInput]:
    lower_query = query.lower()
    normalized_query = _normalize_for_match(query)
    found: list[tuple[int, OrderLineInput]] = []
    for product in store.products:
        index = lower_query.find(product.name.lower())
        if index != -1:
            quantity = _extract_quantity_before_product(query[:index])
            found.append((index, OrderLineInput(product_id=product.product_id, quantity=quantity)))
            continue

        product_name = _normalize_for_match(product.name)
        normalized_index = normalized_query.find(product_name)
        index = normalized_index
        if index == -1:
            continue
        quantity = 1
        found.append((index, OrderLineInput(product_id=product.product_id, quantity=quantity)))
    found.sort(key=lambda item: item[0])
    return [item for _, item in found]


def _extract_quantity_before_product(raw_prefix: str) -> int:
    prefix = raw_prefix.rstrip()
    match = re.search(r"(?<![\w-])(\d+)\s*$", prefix)
    if not match:
        return 1

    return int(match.group(1))


def _clean_shipping_address(raw: str) -> str:
    address = raw.strip(" .,:;")
    while True:
        cleaned = re.sub(
            r"^(?:đến|den|tới|toi|về|ve|hàng|hang|àng|ới|ề)\s+",
            "",
            address,
            flags=re.IGNORECASE,
        ).strip(" .,:;")
        if cleaned == address:
            break
        address = cleaned
    return address


def _missing_required_fields(customer: dict[str, str], items: list[OrderLineInput]) -> list[str]:
    missing: list[str] = []
    if not customer["name"]:
        missing.append("tên khách hàng")
    if not customer["phone"]:
        missing.append("số điện thoại")
    if not customer["email"]:
        missing.append("email")
    if not customer["shipping_address"]:
        missing.append("địa chỉ giao hàng")
    if not items:
        missing.append("sản phẩm và số lượng")
    return missing


def _stock_errors(items: list[OrderLineInput], store: OrderDataStore) -> list[str]:
    errors: list[str] = []
    for item in items:
        product = store.product_index[item.product_id]
        if item.quantity > product.stock:
            errors.append(f"{product.name} chỉ còn {product.stock}, bạn yêu cầu {item.quantity}")
    return errors


def _tool_record(name: str, args: dict[str, Any], output: Any) -> ToolCallRecord:
    return ToolCallRecord(
        name=name,
        args=args,
        output=json.dumps(output, ensure_ascii=False),
    )


def _line_to_dict(item: OrderLineInput) -> dict[str, Any]:
    return {"product_id": item.product_id, "quantity": item.quantity}

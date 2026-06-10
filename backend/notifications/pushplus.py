"""PushPlus 微信提醒封装。"""

import logging
from datetime import datetime
from typing import Any

import httpx

from backend import config
from backend.core.market_hours import CST


logger = logging.getLogger(__name__)  # 当前模块日志记录器

CIRCUIT_BREAKER_RESUME_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"  # 熔断恢复时间展示格式


TYPE_LABEL: dict[str, str] = {
    "BUY": "建仓",
    "ADD_LOT": "加仓",
    "TAKE_PROFIT_1": "1轮止盈",
    "TAKE_PROFIT_2": "2轮止盈",
    "TAKE_PROFIT_TRAILING": "追踪止盈",
    "STOP_LOSS_HALF": "半仓止损",
    "STOP_LOSS_CLEAR": "清仓止损",
    "TREND_CLEAR": "趋势清仓",
    "CIRCUIT_BREAKER_1": "一级熔断",
    "CIRCUIT_BREAKER_2": "二级熔断",
    "CIRCUIT_BREAKER_3": "三级熔断",
}  # 与前端信号面板保持一致的信号文案

BUY_SIGNAL_TYPES = {"BUY", "ADD_LOT"}  # 不展示盈亏字段的买入类信号


def _format_money(value: float | None) -> str:
    """格式化人民币金额，空值展示为占位符。"""
    if value is None:
        return "--"
    return f"{value:.2f}"


def _get_type_label(sig_type: str) -> str:
    """获取信号类型中文文案，未知类型回退为原始枚举值。"""
    return TYPE_LABEL.get(sig_type, sig_type)


def _format_resume_time(resume_ts: int) -> str:
    """格式化熔断恢复时间。"""
    return datetime.fromtimestamp(resume_ts / 1000, tz=CST).strftime(CIRCUIT_BREAKER_RESUME_TIME_FORMAT)


def build_signal_message_content(
    sig_type: str,
    price: float,
    amount_g: float,
    pnl_yuan: float | None,
    reason: str,
) -> str:
    """构建交易信号微信提醒正文。"""
    type_label = _get_type_label(sig_type)
    if sig_type in BUY_SIGNAL_TYPES:
        return (
            f"当前金价￥{price:.2f}，触发了{type_label}，"
            f"克数：{amount_g:g} g，原因：{reason}。"
        )
    return (
        f"当前金价￥{price:.2f}，触发了{type_label}，"
        f"克数：{amount_g:g} g，盈亏：￥{_format_money(pnl_yuan)}，原因：{reason}。"
    )


def build_circuit_breaker_message_content(
    level: int,
    price: float | None,
    reason: str,
    resume_ts: int,
) -> str:
    """构建熔断信号微信提醒正文。"""
    sig_type = f"CIRCUIT_BREAKER_{level}"
    type_label = _get_type_label(sig_type)
    return (
        f"当前金价￥{_format_money(price)}，触发了{type_label}，"
        f"原因：{reason}，恢复时间：{_format_resume_time(resume_ts)}。"
    )


def send_pushplus_message(title: str, content: str) -> bool:
    """通过 PushPlus 多渠道接口发送微信提醒。"""
    if not config.PUSHPLUS_TOKEN:
        logger.warning("PushPlus token 未配置，跳过微信提醒")
        return False

    payload: dict[str, Any] = {
        "token": config.PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "topic": config.PUSHPLUS_TOPIC,
        "template": config.PUSHPLUS_TEMPLATE,
        "channel": config.PUSHPLUS_CHANNEL,
        "option": config.PUSHPLUS_OPTION,
    }  # PushPlus batchSend 请求体

    try:
        response = httpx.post(
            config.PUSHPLUS_BATCH_SEND_URL,
            json=payload,
            timeout=config.PUSHPLUS_TIMEOUT_SEC,
        )
        response.raise_for_status()
        body = response.json()
    except Exception:
        logger.exception("PushPlus 微信提醒发送失败")
        return False

    if body.get("code") != 200:
        logger.warning("PushPlus 微信提醒返回异常：%s", body)
        return False
    return True


def send_signal_notice(
    sig_type: str,
    price: float,
    amount_g: float,
    pnl_yuan: float | None,
    reason: str,
) -> bool:
    """发送交易信号微信提醒。"""
    type_label = _get_type_label(sig_type)
    title = f"金价:{price:.2f} {type_label}"
    content = build_signal_message_content(sig_type, price, amount_g, pnl_yuan, reason)
    return send_pushplus_message(title, content)


def send_circuit_breaker_notice(
    level: int,
    price: float | None,
    reason: str,
    resume_ts: int,
) -> bool:
    """发送熔断信号微信提醒。"""
    sig_type = f"CIRCUIT_BREAKER_{level}"
    type_label = _get_type_label(sig_type)
    title = f"金价:{_format_money(price)} {type_label}"
    content = build_circuit_breaker_message_content(level, price, reason, resume_ts)
    return send_pushplus_message(title, content)

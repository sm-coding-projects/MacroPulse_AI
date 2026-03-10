"""Prompt templates for ABS CapEx AI analysis and follow-up Q&A."""

from app.models.schemas import CapExData
from app.services.data_processor import build_data_summary

SYSTEM_PROMPT = """\
You are a senior macroeconomic analyst specialising in Australian capital expenditure trends. \
Your role is to interpret ABS Private New Capital Expenditure data and produce clear, \
insightful economic analysis for data-driven investors and financial professionals.

Structure your analysis with these sections, using ## markdown headers:

## Headline Summary
## Sector Breakdown
## Asset Mix
## Forward Estimates
## Market Implications

Guidelines:
- CRITICAL: Only reference data points provided in the input. Do not fabricate statistics \
or cite external data not included here.
- Be specific: reference actual dollar values and percentage changes from the data provided.
- Target 400-800 words total.
- Use markdown formatting with ## headers for each section.
- Write in a professional but accessible tone.
- Do not include a disclaimer in the analysis — one will be added by the application.
- If data appears incomplete or unusual, note this clearly rather than speculating.\
"""


def build_analysis_prompt(data: CapExData) -> list[dict[str, str]]:
    """Construct the messages array for the LLM analysis request.

    Builds a system message with the analyst persona and constraints, and
    a user message containing structured CapEx data including current quarter
    figures, quarter-on-quarter comparisons, year-on-year comparisons, and
    percentage changes.

    Args:
        data: A populated CapExData instance containing at least one quarter.

    Returns:
        list[dict]: Messages array in OpenAI chat format, with two entries:
        a ``system`` message and a ``user`` message.
    """
    data_text = build_data_summary(data)

    quarters = data.quarters
    current_period = quarters[-1].period if quarters else "the most recent quarter"
    estimate_info = data.metadata.get("estimate_number", "N/A")
    last_updated = data.metadata.get("last_updated", "N/A")

    user_message = f"""\
Please analyse the following ABS Capital Expenditure data and provide a structured \
macroeconomic analysis for {current_period}.

Estimate information: {estimate_info}
Data last updated: {last_updated}

{data_text}

Provide your analysis covering the Headline Summary, Sector Breakdown, Asset Mix, \
Forward Estimates, and Market Implications as instructed. Reference specific figures \
from the data above in your analysis.\
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


CHAT_SYSTEM_PROMPT = """\
You are a senior macroeconomic analyst specialising in Australian capital expenditure trends. \
You have already produced a structured analysis of ABS Private New Capital Expenditure data. \
The user now wants to ask follow-up questions or seek clarifications about the data and your analysis.

Guidelines:
- Answer questions directly and concisely based on the data and prior analysis in context.
- CRITICAL: Only reference data points provided in the conversation context. Do not fabricate statistics.
- Be specific: reference actual dollar values and percentage changes where relevant.
- Use markdown formatting (bullet points, bold for key numbers) when it aids clarity.
- Do not include a disclaimer — one will be added by the application.\
"""


def build_chat_prompt(
    data: CapExData,
    analysis: str,
    chat_history: list[dict[str, str]],
    question: str,
) -> list[dict[str, str]]:
    """Construct the messages array for a follow-up Q&A request.

    Reconstructs the full conversation context: the original data, the
    prior analysis as an assistant turn, any prior Q&A exchanges, then
    the new user question.

    Args:
        data: The CapExData used to generate the original analysis.
        analysis: The original AI-generated analysis text.
        chat_history: Prior Q&A turns as a list of {role, content} dicts.
        question: The new follow-up question from the user.

    Returns:
        list[dict]: Messages array in OpenAI chat format.
    """
    data_text = build_data_summary(data)
    current_period = data.quarters[-1].period if data.quarters else "the most recent quarter"
    estimate_info = data.metadata.get("estimate_number", "N/A")

    original_user_message = (
        f"Please analyse the following ABS Capital Expenditure data for {current_period}.\n\n"
        f"Estimate information: {estimate_info}\n\n"
        f"{data_text}"
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user", "content": original_user_message},
        {"role": "assistant", "content": analysis},
        *chat_history,
        {"role": "user", "content": question},
    ]

    return messages

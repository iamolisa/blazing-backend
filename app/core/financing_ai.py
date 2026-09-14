"""
Financing/installment advisor: takes a free-text description of a client's
situation (budget, timeline, what they want to run) and returns a
plain-language recommendation grounded in Blazing Trail's actual current
packages and pricing, not invented numbers, and not a binding financing
offer (the business doesn't have standing financing infrastructure; see
DEPLOY.md).

Runs on Groq (free tier) rather than a paid provider, since this is a
budget-conscious small business tool. This is the only file that knows
which AI provider is in use. Swapping to Anthropic or another provider
later (e.g. once the business can afford it) means changing this one
file, not anything that calls it.

Kept deliberately narrow in scope:
- Reads real package data from the DB and puts it in the prompt, so the
  model can't hallucinate prices.
- System prompt explicitly forbids quoting an interest rate, approving
  credit, or promising installment terms. This is a "here's what fits
  your load and here's a rough monthly split IF financing is available"
  tool, not a loan calculator. The business owner said financing is
  case-by-case, not standing policy. The AI's output has to reflect that
  every time, not just when it remembers to.
- Fails loudly and cheaply: if GROQ_API_KEY isn't set, callers get a
  clear "not configured" signal instead of a stack trace, and the call
  itself has a short timeout so a slow/down provider can't hang a request.
"""
import groq
from flask import current_app

MAX_INPUT_CHARS = 800
REQUEST_TIMEOUT_SECONDS = 20


class FinancingAdvisorUnavailable(Exception):
    """Raised when the advisor can't run (no API key configured, or the
    provider call itself failed). routes.py turns this into a clean
    error response instead of a 500."""
    pass


def _format_packages_for_prompt(packages):
    lines = []
    for p in packages:
        price_bits = []
        if p.price_with_panel_naira:
            price_bits.append(f"₦{p.price_with_panel_naira:,} with panels")
        if p.price_without_panel_naira:
            price_bits.append(f"₦{p.price_without_panel_naira:,} without panels")
        price_text = " / ".join(price_bits) if price_bits else "price on request"
        lines.append(f"- {p.name} ({p.kva_rating}, {p.battery_type} battery): {price_text}")
    return "\n".join(lines) if lines else "No packages currently loaded."


def _build_system_prompt(packages):
    return (
        "You are a financing advisor widget on Blazing Trail Engineering's website, "
        "a Nigerian solar and electrical engineering company. A visitor has described "
        "their budget, timeline, or what they want to run, and you recommend which of "
        "the company's real packages fits, with a rough monthly breakdown IF they were "
        "to spread the cost.\n\n"
        "CURRENT PACKAGES AND PRICING (Nigerian Naira, use these exact figures, never invent others):\n"
        f"{_format_packages_for_prompt(packages)}\n\n"
        "Hard rules:\n"
        "1. Only reference the packages and prices listed above. Never invent a price, "
        "package, spec, or discount not in that list.\n"
        "2. Blazing Trail does not have standing financing/installment infrastructure. "
        "Any monthly breakdown you give is illustrative only (simple division of the "
        "package price across the months the visitor mentioned). Never state or imply "
        "an interest rate, credit approval, or a binding payment plan. Always say plainly "
        "that installment arrangements are considered case-by-case and confirmed directly "
        "with the team, not guaranteed by this tool.\n"
        "3. If the visitor's message doesn't give you enough to recommend a specific "
        "package (no sense of budget, load, or site), ask ONE clarifying question instead "
        "of guessing.\n"
        "4. Keep the response short: 3-5 sentences plus, if relevant, a simple monthly "
        "breakdown. No headers, no markdown, plain conversational text suitable for a "
        "small chat widget.\n"
        "5. End by pointing them to submit their phone number so the team can follow up "
        "and confirm real terms. You are not the final word on pricing or financing."
    )


def get_financing_advice(user_message, packages):
    """
    Returns the advisor's plain-text response, or raises
    FinancingAdvisorUnavailable if the feature isn't configured or the
    provider call fails.
    """
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        raise FinancingAdvisorUnavailable(
            "The financing advisor isn't configured yet. Set GROQ_API_KEY in the "
            "environment to enable it."
        )

    message = (user_message or "").strip()
    if not message:
        raise FinancingAdvisorUnavailable("Please describe your budget, timeline, or what you'd like to run.")
    if len(message) > MAX_INPUT_CHARS:
        message = message[:MAX_INPUT_CHARS]

    client = groq.Groq(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)

    try:
        response = client.chat.completions.create(
            model=current_app.config["GROQ_MODEL"],
            max_tokens=400,
            messages=[
                {"role": "system", "content": _build_system_prompt(packages)},
                {"role": "user", "content": message},
            ],
        )
    except groq.GroqError as exc:
        current_app.logger.error(f"Financing advisor: Groq API error: {exc}")
        raise FinancingAdvisorUnavailable(
            "The financing advisor is temporarily unavailable, please try again shortly, "
            "or request a quote directly."
        )

    reply = (response.choices[0].message.content or "").strip()
    return reply or (
        "I couldn't put together a recommendation from that. Could you share your rough "
        "budget or what you'd like to power?"
    )

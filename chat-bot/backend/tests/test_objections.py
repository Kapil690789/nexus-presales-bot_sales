from backend.app.config_loader.loader import load_config
from backend.app.engines.objections import match_objection


def test_price_objection() -> None:
    hit = match_objection("This is way too expensive compared to others", load_config().objections)
    assert hit is not None
    assert "range" in hit["reply"].lower() or "indicative" in hit["reply"].lower()


def test_unknown_text_is_not_an_objection() -> None:
    assert match_objection("We need appointment reminders", load_config().objections) is None

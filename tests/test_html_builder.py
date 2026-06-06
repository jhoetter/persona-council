"""C1 — the auto-escaping element builder (spec/component-ssr-architecture.md)."""
from persona_council.web._html import h, esc, raw, fragment, Safe


def test_text_children_are_escaped():
    assert h("p", {}, "a < b & c") == '<p>a &lt; b &amp; c</p>'


def test_xss_payload_in_text_is_neutralised():
    out = h("div", {}, '<script>alert(1)</script>')
    assert "<script>" not in out and "&lt;script&gt;" in out


def test_raw_passes_trusted_html_through():
    assert h("div", {}, raw("<b>ok</b>")) == "<div><b>ok</b></div>"


def test_safe_children_are_not_double_escaped():
    inner = h("span", {}, "x & y")
    assert h("div", {}, inner) == "<div><span>x &amp; y</span></div>"


def test_attrs_escape_quote_and_map_class_and_underscores():
    out = h("a", {"class_": "row", "data_id": "1", "href": '">x'})
    assert 'class="row"' in out and 'data-id="1"' in out and 'href="&quot;&gt;x"' in out


def test_none_and_false_attrs_and_children_are_skipped():
    assert h("div", {"hidden": None, "x": False}, None, False, "ok") == "<div>ok</div>"


def test_boolean_true_attr_is_bare():
    assert h("input", {"disabled": True}) == "<input disabled>"


def test_void_elements_have_no_closing_tag():
    assert h("br") == "<br>" and h("img", {"src": "a"}) == '<img src="a">'


def test_iterables_of_children_are_flattened():
    rows = [h("li", {}, str(i)) for i in range(3)]
    assert h("ul", {}, rows) == "<ul><li>0</li><li>1</li><li>2</li></ul>"


def test_fragment_groups_without_a_wrapper():
    assert fragment(h("i", {}, "a"), "b<") == "<i>a</i>b&lt;"


def test_outputs_are_safe_and_esc_is_idempotent():
    assert isinstance(h("p", {}, "x"), Safe)
    assert esc(esc("a<b")) == "a&lt;b"

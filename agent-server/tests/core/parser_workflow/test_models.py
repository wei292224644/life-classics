from app.core.parser_workflow.models import make_chunk_id


def test_chunk_id_is_16_hex_chars():
    cid = make_chunk_id("GB2760", ["3 范围"], "本标准规定食品添加剂的使用。")
    assert len(cid) == 16
    assert all(c in "0123456789abcdef" for c in cid)


def test_chunk_id_same_input_same_output():
    a = make_chunk_id("GB2760", ["3 范围"], "内容")
    b = make_chunk_id("GB2760", ["3 范围"], "内容")
    assert a == b


def test_chunk_id_different_content_different_id():
    a = make_chunk_id("GB2760", ["3 范围"], "内容A")
    b = make_chunk_id("GB2760", ["3 范围"], "内容B")
    assert a != b


def test_chunk_id_different_section_different_id():
    a = make_chunk_id("GB2760", ["3 范围"], "内容")
    b = make_chunk_id("GB2760", ["4 定义"], "内容")
    assert a != b


import pytest

from app.services.chunking import chunk_text


def test_short_text_returns_one_chunk() -> None:
    assert chunk_text("Library hours are 9 AM", chunk_size=5, overlap=1) == [
        "Library hours are 9 AM"
    ]


def test_long_text_splits_into_configured_windows() -> None:
    words = [f"word{index}" for index in range(11)]

    chunks = chunk_text(" ".join(words), chunk_size=4, overlap=1)

    assert chunks == [
        "word0 word1 word2 word3",
        "word3 word4 word5 word6",
        "word6 word7 word8 word9",
        "word9 word10",
    ]
    assert [word for chunk in chunks for word in chunk.split()] == [
        *words[:4],
        *words[3:7],
        *words[6:10],
        *words[9:],
    ]


def test_overlap_preserves_boundary_words() -> None:
    assert chunk_text("a b c d e", chunk_size=3, overlap=1) == [
        "a b c",
        "c d e",
    ]


def test_whitespace_is_normalized_without_empty_chunks() -> None:
    assert chunk_text(" \n alpha\t beta   gamma ", chunk_size=2, overlap=0) == [
        "alpha beta",
        "gamma",
    ]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (3, -1), (3, 3), (True, 0), (3, False)],
)
def test_invalid_parameters_raise(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_text("some words", chunk_size=chunk_size, overlap=overlap)


@pytest.mark.parametrize("text", ["", "  \n\t  "])
def test_empty_text_raises(text: str) -> None:
    with pytest.raises(ValueError, match="not be empty"):
        chunk_text(text)
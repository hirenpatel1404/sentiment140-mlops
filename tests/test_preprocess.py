"""Unit tests for the shared cleaning function."""
from src.preprocess import clean_tweet, tokenize, preprocess


def test_removes_urls_mentions_and_html():
    out = clean_tweet("@john check http://t.co/abc www.site.com &amp; more")
    assert "john" not in out and "http" not in out and "www" not in out and "&" not in out
    assert out == "check more"


def test_lowercase_and_special_characters():
    assert clean_tweet("WOW!!! Great :) 100%") == "wow great"


def test_keeps_negations_as_one_word():
    assert "cant" in tokenize("I CAN'T believe it")
    assert "dont" in tokenize("I don't like it")


def test_hashtag_word_is_kept():
    assert "blessed" in tokenize("so happy #blessed")


def test_repeated_letters_are_shortened():
    assert "soo" in tokenize("sooooo good")


def test_empty_and_non_string_input():
    assert preprocess("") == ""
    assert preprocess(None) == ""
    assert preprocess("@user http://x.com") == ""

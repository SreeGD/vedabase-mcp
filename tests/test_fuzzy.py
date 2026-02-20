"""Tests for Sanskrit transliteration normalization and fuzzy matching."""

from vedabase_mcp.fuzzy import fuzzy_match, normalize_sanskrit, score_match


class TestNormalization:
    def test_lowercase(self):
        assert normalize_sanskrit("Karmaṇy") == "karmany"

    def test_diacritics_removed(self):
        assert normalize_sanskrit("ā") == "a"
        assert normalize_sanskrit("ī") == "i"
        assert normalize_sanskrit("ū") == "u"
        assert normalize_sanskrit("ṛ") == "ri"
        assert normalize_sanskrit("ṣ") == "sh"
        assert normalize_sanskrit("ś") == "sh"
        assert normalize_sanskrit("ṇ") == "n"
        assert normalize_sanskrit("ṅ") == "n"
        assert normalize_sanskrit("ñ") == "n"
        assert normalize_sanskrit("ḍ") == "d"
        assert normalize_sanskrit("ṁ") == "m"
        assert normalize_sanskrit("ḥ") == "h"

    def test_punctuation_removed(self):
        assert normalize_sanskrit("karma-yoga") == "karmayoga"

    def test_spaces_collapsed(self):
        assert normalize_sanskrit("karmaṇy   evādhikāras   te") == "karmany evadhikaras te"

    def test_full_normalization(self):
        result = normalize_sanskrit("Karmaṇy evādhikāras te")
        assert result == "karmany evadhikaras te"

    def test_verse_numbers_stripped(self):
        # Verse numbers like ||2-47|| contain digits and punctuation
        result = normalize_sanskrit("text ||2-47||")
        assert result == "text"


class TestScoring:
    def test_exact_match(self):
        score = score_match("karmaṇyevādhikāraste", "karmaṇyevādhikāraste")
        assert score == 1.0

    def test_empty_strings(self):
        assert score_match("", "anything") == 0.0
        assert score_match("anything", "") == 0.0

    def test_garbled_bg_9_34(self):
        garbled = "man manā bhava mad-bhākto mad-yajī mam namāskuru"
        correct = "manmanā bhava madbhakto madyājī māṁ namaskuru"
        score = score_match(garbled, correct)
        assert score > 0.5

    def test_garbled_bg_2_47(self):
        garbled = "kārama-ñeva-dhikāra-ste māpaleṣu-dhikāṣṭhana"
        correct = "karmaṇyevādhikāraste mā phaleṣu kadācana"
        score = score_match(garbled, correct)
        assert score > 0.25


class TestFuzzyMatch:
    SAMPLE_VERSES = [
        ("BG 2.47", "karmaṇyevādhikāraste mā phaleṣu kadācana mā karmaphalaheturbhūrmā te saṅgo'stvakarmaṇi"),
        ("BG 9.34", "manmanā bhava madbhakto madyājī māṁ namaskuru mām evaiṣyasi yuktvaivam ātmānaṁ matparāyaṇaḥ"),
        ("BG 15.7", "mamaivāṁśo jīvaloke jīvabhūtaḥ sanātanaḥ manaḥṣaṣṭhānīndriyāṇi prakṛtisthāni karṣati"),
        ("BG 4.7", "yadā yadā hi dharmasya glānirbhavati bhārata abhyutthānam adharmasya tadātmānaṁ sṛjāmyaham"),
    ]

    def test_match_bg_9_34(self):
        garbled = "man manā bhava mad-bhākto mad-yajī mam namāskuru"
        matches = fuzzy_match(garbled, self.SAMPLE_VERSES, top_n=3)
        assert len(matches) > 0
        assert matches[0]["ref"] == "BG 9.34"

    def test_match_bg_15_7(self):
        garbled = "mā mā evaṁ sa jīva-loka jīva-bhūta-sanātana"
        matches = fuzzy_match(garbled, self.SAMPLE_VERSES, top_n=3)
        assert len(matches) > 0
        assert matches[0]["ref"] == "BG 15.7"

    def test_match_bg_2_47(self):
        garbled = "kārama-ñeva-dhikāra-ste māpaleṣu"
        matches = fuzzy_match(garbled, self.SAMPLE_VERSES, top_n=3)
        assert len(matches) > 0
        assert matches[0]["ref"] == "BG 2.47"

    def test_top_n_limits_results(self):
        garbled = "bhava"
        matches = fuzzy_match(garbled, self.SAMPLE_VERSES, top_n=2)
        assert len(matches) <= 2

    def test_threshold_filters(self):
        matches = fuzzy_match("zzzzz", self.SAMPLE_VERSES, top_n=5, threshold=0.5)
        assert len(matches) == 0

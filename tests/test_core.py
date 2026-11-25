import os
import unittest

from crm_dedupe import normalize_name, normalize_domain, find_duplicates, naive_duplicates, load_csv
from crm_dedupe.__main__ import main

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
CRM = os.path.join(DATA, "crm_example.csv")
ERP = os.path.join(DATA, "erp_example.csv")


class Normalize(unittest.TestCase):
    def test_name_suffix_accent_punctuation(self):
        self.assertEqual(normalize_name("Açme Industrial, Ltd."), "acme industrial")
        self.assertEqual(normalize_name("Cobalt Logistics S.A."), "cobalt logistics")
        self.assertEqual(normalize_name("Foo S.R.L."), "foo")
        self.assertEqual(normalize_name("Smith & Sons LLC"), "smith and sons")

    def test_name_empty(self):
        self.assertEqual(normalize_name(None), "")
        self.assertEqual(normalize_name("Inc"), "")

    def test_domain(self):
        self.assertEqual(normalize_domain("https://www.Acme.example/path?x=1"), "acme.example")
        self.assertEqual(normalize_domain("bill@acme.example"), "acme.example")
        self.assertEqual(normalize_domain("x@gmail.com"), "")
        self.assertEqual(normalize_domain(""), "")


class Clusters(unittest.TestCase):
    def rec(self, name, site="", country=""):
        return {"name": name, "website": site, "country": country}

    def test_same_domain_wins_over_different_names(self):
        c = find_duplicates([self.rec("A Corp", "a.example"), self.rec("Totally Different", "www.a.example")])
        self.assertEqual(len(c), 1)
        self.assertIn("same domain", c[0]["reasons"])

    def test_fuzzy_needs_compatible_country(self):
        a = self.rec("Evergreen Pharma", country="US")
        b = self.rec("Evergreen Pharmaceuticals", country="BR")
        self.assertEqual(find_duplicates([a, b], 0.7), [])
        b["country"] = ""
        self.assertEqual(len(find_duplicates([a, b], 0.7)), 1)

    def test_transitive_cluster(self):
        rs = [self.rec("Foo", "foo.example"), self.rec("Bar", "foo.example"), self.rec("Bar Ltd")]
        c = find_duplicates(rs)
        self.assertEqual([sorted(x["members"]) for x in c], [[0, 1, 2]])

    def test_free_mail_never_links(self):
        rs = [{"name": "One", "email": "a@gmail.com"}, {"name": "Two", "email": "b@gmail.com"}]
        self.assertEqual(find_duplicates(rs), [])

    def test_empty(self):
        self.assertEqual(find_duplicates([]), [])


class ExampleData(unittest.TestCase):
    def setUp(self):
        self.records = load_csv(CRM) + load_csv(ERP)

    def test_baseline_finds_nothing_but_tool_finds_clusters(self):
        # Exact raw-name match only catches the two "Granite Bank" rows.
        base = naive_duplicates(self.records)
        self.assertEqual(len(base), 1)
        clusters = find_duplicates(self.records)
        self.assertEqual(len(clusters), 6)

    def test_granite_bank_in_two_countries_is_not_merged(self):
        # The exact-name baseline merges them; the tool keeps them apart (US vs CA).
        names = [self.records[i]["name"] for c in find_duplicates(self.records) for i in c["members"]]
        self.assertNotIn("Granite Bank", names)

    def test_known_miss_pharma_variant(self):
        # "Evergreen Pharmaceuticals" (no country) is not linked at the default threshold.
        ids = {self.records[i]["id"] for c in find_duplicates(self.records) for i in c["members"]}
        self.assertNotIn("106", ids)

    def test_cli_runs(self):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main([CRM, ERP]), 0)
        self.assertIn("Clusters found: 6", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

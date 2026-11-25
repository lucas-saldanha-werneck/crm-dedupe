# crm-dedupe

Finds duplicate company records when you merge a CRM export with an ERP export. Python standard library only, about 150 lines.

Independent demo, not affiliated with Nortal. I built it after applying for a role that involves connecting AI agents to CRM and ERP data, where the same customer often shows up twice under different spellings.

All data in `data/` is invented example data.

## Run

```
python3 -m crm_dedupe data/crm_example.csv data/erp_example.csv
python3 -m unittest discover -s tests -v
```

Each CSV needs a `name` column, a `website` or `email` column, and optionally `country`. The output is a Markdown report with the clusters, why each one matched, and a comparison with a plain exact-name match.

## How it matches

1. Same domain (from the website or the e-mail address). Free mail domains like gmail.com are ignored.
2. Same name after lowercasing and removing accents, punctuation and legal suffixes (Ltd, GmbH, S.A., Ltda...), if the countries agree or one is empty.
3. Similar name (difflib ratio at or above 0.88, adjustable with `--threshold`), with the same country rule.

Matches chain: if A matches B and B matches C, all three form one cluster.

## What was tested

- 12 offline unit tests, run in CI on every push: name and domain normalization, each matching rule, chaining, free-mail handling, empty input, and the command line.
- On the example files (15 records), the tool finds 6 clusters (12 records). An exact-name match finds 1 cluster.
- It found two bugs in my first version while I wrote the tests. "S.A." was read as two tokens, so "Cobalt Logistics S.A." did not lose its suffix. The exact-name rule also merged two "Granite Bank" records from the US and Canada. Both are fixed and covered by tests.

## What was not tested

- Real CRM or ERP exports. The example data is small and written by me, so the numbers above say nothing about accuracy on real data.
- Large files. The comparison is pairwise, so it grows with the square of the record count. Fine for thousands of rows, not for millions.
- Names in non-Latin scripts, and legal suffixes outside the short built-in list.
- A known miss: "Evergreen Pharma" and "Evergreen Pharmaceuticals" are not linked at the default threshold. A test records this.
- Choosing which record survives a merge. The tool only reports clusters and does not change any data.

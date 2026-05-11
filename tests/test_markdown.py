import unittest

from brainiac.markdown import extract_markdown_facts


class MarkdownExtractionTest(unittest.TestCase):
    def test_extracts_markdown_facts_without_code_fences(self):
        facts = extract_markdown_facts(
            """# Title

Text with [[Target Note|alias]] and #todo/now.
- [ ] open task
- [x] done task

```text
# Not a heading
[[Not a link]]
```
"""
        )

        self.assertEqual(
            [(heading.level, heading.text, heading.line) for heading in facts.headings],
            [(1, "Title", 1)],
        )
        self.assertEqual(
            [(link.target, link.alias, link.line) for link in facts.wikilinks],
            [("Target Note", "alias", 3)],
        )
        self.assertEqual([(tag.value, tag.line) for tag in facts.tags], [("#todo/now", 3)])
        self.assertEqual(
            [(task.done, task.text, task.line) for task in facts.tasks],
            [(False, "open task", 4), (True, "done task", 5)],
        )

    def test_extracts_frontmatter_tags_and_ignores_tilde_fences(self):
        facts = extract_markdown_facts(
            """---
tags:
  - todo/soon
  - "#project/brainiac"
aliases:
  - not-a-tag
---

~~~markdown
# Not a heading
[[Not a link]]
#not/a/tag
~~~

# Real Heading
Text #real/tag
"""
        )

        self.assertEqual(
            [(tag.value, tag.line) for tag in facts.tags],
            [("#todo/soon", 3), ("#project/brainiac", 4), ("#real/tag", 16)],
        )
        self.assertEqual(
            [(heading.level, heading.text, heading.line) for heading in facts.headings],
            [(1, "Real Heading", 15)],
        )
        self.assertEqual(facts.wikilinks, ())


if __name__ == "__main__":
    unittest.main()

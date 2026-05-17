from __future__ import annotations

import re
from dataclasses import dataclass


FRONTMATTER_DELIMITER_RE = re.compile(r"^---\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
TAG_RE = re.compile(r"(?<![\w/-])#([A-Za-zА-Яа-я0-9][\wА-Яа-я/-]*)")
FRONTMATTER_TAG_RE = re.compile(r"(?<![\w/-])#?([A-Za-zА-Яа-я0-9][\wА-Яа-я/-]*)")
TASK_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$")


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int


@dataclass(frozen=True)
class WikiLink:
    target: str
    alias: str | None
    line: int


@dataclass(frozen=True)
class Tag:
    value: str
    line: int


@dataclass(frozen=True)
class Task:
    text: str
    done: bool
    line: int


@dataclass(frozen=True)
class MarkdownFacts:
    headings: tuple[Heading, ...]
    wikilinks: tuple[WikiLink, ...]
    tags: tuple[Tag, ...]
    tasks: tuple[Task, ...]
    frontmatter: dict[str, tuple[str, ...]]


def extract_markdown_facts(text: str) -> MarkdownFacts:
    headings: list[Heading] = []
    wikilinks: list[WikiLink] = []
    tags: list[Tag] = []
    tasks: list[Task] = []
    frontmatter: dict[str, list[str]] = {}
    fence_marker: str | None = None
    in_frontmatter = False
    in_frontmatter_tags_list = False
    frontmatter_list_key: str | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        if line_number == 1 and FRONTMATTER_DELIMITER_RE.match(line):
            in_frontmatter = True
            continue
        if in_frontmatter:
            if FRONTMATTER_DELIMITER_RE.match(line):
                in_frontmatter = False
                in_frontmatter_tags_list = False
                frontmatter_list_key = None
                continue
            frontmatter_list_key = _extract_frontmatter_value(line, frontmatter, frontmatter_list_key)
            extracted, in_frontmatter_tags_list = _extract_frontmatter_tags(
                line,
                line_number,
                in_frontmatter_tags_list,
            )
            tags.extend(extracted)
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence_marker is None:
                fence_marker = marker
            elif marker == fence_marker:
                fence_marker = None
            continue
        if fence_marker is not None:
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            headings.append(
                Heading(
                    level=len(heading_match.group(1)),
                    text=heading_match.group(2).strip(),
                    line=line_number,
                )
            )

        task_match = TASK_RE.match(line)
        if task_match:
            tasks.append(
                Task(
                    text=task_match.group(2).strip(),
                    done=task_match.group(1).lower() == "x",
                    line=line_number,
                )
            )

        for link_match in WIKILINK_RE.finditer(line):
            raw_target = link_match.group(1).strip()
            target, alias = _split_wikilink(raw_target)
            wikilinks.append(WikiLink(target=target, alias=alias, line=line_number))

        for tag_match in TAG_RE.finditer(line):
            tags.append(Tag(value="#" + tag_match.group(1), line=line_number))

    return MarkdownFacts(
        headings=tuple(headings),
        wikilinks=tuple(wikilinks),
        tags=tuple(tags),
        tasks=tuple(tasks),
        frontmatter={key: tuple(values) for key, values in frontmatter.items()},
    )


def _extract_frontmatter_value(
    line: str,
    frontmatter: dict[str, list[str]],
    list_key: str | None,
) -> str | None:
    stripped = line.strip()
    if not stripped:
        return list_key
    if list_key and stripped.startswith("- "):
        value = _clean_frontmatter_scalar(stripped[2:].strip())
        if value:
            frontmatter.setdefault(list_key, []).append(value)
        return list_key
    if ":" not in stripped:
        return None
    key, _, raw_value = stripped.partition(":")
    key = key.strip()
    if not key:
        return None
    value = raw_value.strip()
    if not value:
        frontmatter.setdefault(key, [])
        return key
    for item in _split_frontmatter_values(value):
        frontmatter.setdefault(key, []).append(item)
    return None


def _split_frontmatter_values(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
        return [
            cleaned
            for item in value.split(",")
            if (cleaned := _clean_frontmatter_scalar(item.strip()))
        ]
    cleaned = _clean_frontmatter_scalar(value)
    return [cleaned] if cleaned else []


def _clean_frontmatter_scalar(value: str) -> str:
    return value.strip().strip("'\"")


def _split_wikilink(raw_target: str) -> tuple[str, str | None]:
    target, separator, alias = raw_target.partition("|")
    target = target.strip()
    alias = alias.strip() if separator else None
    if "#" in target:
        target = target.split("#", 1)[0].strip()
    return target, alias


def _extract_frontmatter_tags(
    line: str,
    line_number: int,
    in_tags_list: bool,
) -> tuple[list[Tag], bool]:
    stripped = line.strip()
    if not stripped:
        return [], in_tags_list

    if stripped.startswith("tags:"):
        value = stripped.partition(":")[2].strip()
        if not value:
            return [], True
        in_tags_list = False
    elif in_tags_list and stripped.startswith("- "):
        value = stripped[2:].strip()
    else:
        return [], False

    value = value.strip("[]")
    if not value:
        return [], in_tags_list

    tags = []
    for raw_tag in re.split(r"[,\s]+", value):
        match = FRONTMATTER_TAG_RE.fullmatch(raw_tag.strip("'\""))
        if match:
            tags.append(Tag(value="#" + match.group(1), line=line_number))
    return tags, in_tags_list

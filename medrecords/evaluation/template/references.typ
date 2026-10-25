// Labels, anchors and breadcrumbs.

#import "style.typ": *
#import "numbers.typ": scalar, secondary

#let group-kinds = ("group", "keyed_group")

// Every entry of the report by repr(path): its title, kind and layout.
#let catalogue(entries, path) = {
  let found = (:)

  for entry in entries {
    let here = path + (entry.name,)

    found.insert(repr(here), (title: entry.title, kind: entry.kind, layout: entry.at("layout", default: none)))

    if entry.kind in group-kinds {
      found += catalogue(entry.entries, here)
    }
  }

  found
}

#let entries = catalogue(report.entries, ())

#let entry-label(path) = label("entry" + repr(path))

#let is-prefix(prefix, path) = prefix.len() <= path.len() and path.slice(0, prefix.len()) == prefix

// The segments of a path as titles: leaving out the prefixes that `within` shares, and
// the groups set inline or as an appendix that the path continues into; a name without
// an entry as its text. Each segment is (title, target), the target none
// for a name without an entry.
#let segments(path, within) = {
  let parts = ()

  for index in range(path.len()) {
    let prefix = path.slice(0, index + 1)
    let entry = entries.at(repr(prefix), default: none)
    let continues = prefix.len() < path.len()

    if is-prefix(prefix, within) { continue }
    if entry != none and entry.layout in ("inline", "appendix") and continues { continue }

    if entry == none {
      parts.push((title: scalar(path.at(index)), target: none))
    } else {
      parts.push((title: entry.title, target: entry-label(prefix)))
    }
  }

  parts
}

// A path cell as a breadcrumb: the segments joined by " / ", each linked when its entry
// is set, and the page of the deepest linked segment after it.
#let reference(path, within) = context {
  let parts = segments(path, within).map(part => {
    if part.target != none and query(part.target).len() == 0 { (title: part.title, target: none) } else { part }
  })

  if parts.len() == 0 {
    let entry = entries.at(repr(path), default: none)

    return if entry == none { scalar(path.last()) } else { entry.title }
  }

  let linked = parts.filter(part => part.target != none)

  parts.map(part => if part.target == none { part.title } else { link(part.target, part.title) }).join(" / ")

  if linked.len() > 0 {
    h(space.tight)
    box(secondary[p.~#counter(page).at(linked.last().target).first()])
  }
}

// The breadcrumb an appendix heading reads: every segment of its path from the root,
// the ones before its own title linked back to the headings of their groups.
#let breadcrumb(path) = {
  let parts = segments(path, ())

  parts
    .enumerate()
    .map(((index, part)) => {
      if index < parts.len() - 1 and part.target != none { link(part.target, part.title) } else { part.title }
    })
    .join(" / ")
}

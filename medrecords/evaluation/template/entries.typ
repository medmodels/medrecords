// How entries are set: headings, listings, captions, facts, checks and the appendix.

#import "style.typ": *
#import "numbers.typ": *
#import "references.typ": breadcrumb, entry-label
#import "tables.typ": deflist, keyed-table, numeric-cell, stacked-table, tabular
#import "charts.typ": counts-chart, histogram-chart, picture, rendered, scatter-chart

#let parameter-lines = options.parameter_lines
#let failure-details = options.failure_details
#let run-details = options.run_details
#let section-breaks = options.section_breaks

#let leaf-kinds = ("analytic", "keyed_analytic")

#let wide-kinds = ("table", "plot", "distribution", "histogram", "counts", "scatter")

#let plain-kinds = ("datetime", "timedelta", "float", "failure")

#let emphasized(body) = strong(body)

#let alert(body) = strong(text(fill: palette.alert, body))

#let stacked(items) = stack(dir: ttb, spacing: space.tight, ..items)

#let is-assessment(value) = kind-of(value) == "assessment"

#let is-failure(value) = kind-of(value) == "failure"

#let is-wide(value) = kind-of(value) in wide-kinds

#let is-plain(value) = type(value) != dictionary or kind-of(value) in plain-kinds

#let layout-of(entry) = entry.at("layout", default: "section")

// "seed: 7 · patients requested: 1500" in the small body face.
#let parameter-line(mapping) = secondary(mapping.pairs().map(((name, value)) => [#name: #detail(value)]).join[ · ])

#let exception(failure) = secondary[#failure.exception_type: #failure.message]

#let not-computed = secondary[not computed]

// "not computed" after what failed, and the exception under it with failure_details.
#let failure-text(failure, lead: none) = {
  let line = if lead == none { not-computed } else { [#lead #not-computed] }

  if failure-details { stacked((line, exception(failure))) } else { line }
}

// A heading of an entry: numbered on the outer three levels; deeper, unnumbered,
// unlisted and without a bookmark; labelled by the entry's path.
#let entry-heading(depth, title, path, numbered) = {
  let listed = numbered and depth <= numbered-levels

  [#heading(
      level: depth,
      numbering: if listed { "1.1" } else { none },
      outlined: listed,
      bookmarked: listed,
      title,
    ) #entry-label(path)]
}

#let inputs-line(inputs) = stacked(inputs.map(input => [
  #input.name: #counted(input.node_count, "node"), #counted(input.edge_count, "edge")
]))

#let derivation-parts(derivation) = {
  let parts = ()

  if parameter-lines and derivation.parameters.len() > 0 { parts.push(parameter-line(derivation.parameters)) }

  if run-details and derivation.summary.len() > 0 { parts.push(parameter-line(derivation.summary)) }

  if derivation.failure != none { parts.push(failure-text(derivation.failure)) }

  parts
}

// The facts under a group's heading: its parameters, the summary of its derivation and
// its inputs with run_details, and the failure of its derivation.
#let facts(entry, parent-inputs) = {
  let items = ()

  if entry.kind == "group" and entry.derivation != none {
    let derivation = entry.derivation

    if parameter-lines and derivation.parameters.len() > 0 {
      items.push(("Parameters", parameter-line(derivation.parameters)))
    }

    if run-details {
      items += derivation.summary.pairs().map(((name, value)) => (name, detail(value)))
    }

    if derivation.failure != none { items.push(("Derivation", failure-text(derivation.failure))) }
  }

  if entry.kind == "keyed_group" {
    for keyed in entry.derivations {
      let parts = derivation-parts(keyed.derivation)

      if parts.len() > 0 { items.push((scalar(keyed.key), stacked(parts))) }
    }
  }

  if run-details and entry.inputs.len() > 0 and entry.inputs != parent-inputs {
    items.push(("Inputs", inputs-line(entry.inputs)))
  }

  items
}

#let facts-block(items) = {
  if items.len() > 0 { block(width: 100%, above: 0pt, below: space.base, sticky: true, deflist(items)) }
}

#let description-block(description) = {
  if description != none {
    block(width: 100%, above: 0pt, below: space.base, sticky: true, secondary(description))
  }
}

// The description and facts an inline group passes on, or none.
#let inline-extra(entry, parent-inputs) = {
  let items = facts(entry, parent-inputs)

  if entry.description == none and items.len() == 0 { return none }

  (description: entry.description, facts: items)
}

#let extra-parts(extras) = {
  let parts = ()

  for extra in extras {
    if extra.description != none { parts.push(secondary(extra.description)) }
    if extra.facts.len() > 0 { parts.push(deflist(extra.facts)) }
  }

  parts
}

// Title, description, parameters and failure of an entry, then what inline groups pass
// on to it, labelled by the entry's path.
#let caption(entry, path, extras) = {
  let items = (emphasized(entry.title),)

  if entry.description != none { items.push(secondary(entry.description)) }

  if parameter-lines and entry.parameters.len() > 0 { items.push(parameter-line(entry.parameters)) }

  if entry.kind == "analytic" and is-failure(entry.result) and failure-details {
    items.push(exception(entry.result))
  }

  items += extra-parts(extras)

  [#block(stacked(items)) #entry-label(path)]
}

#let figures(value, body) = if numeric(value) { numeric-cell(body) } else { body }

#let measurement(value) = {
  let shown(number) = in-unit(number, value.unit)
  let items = (emphasized(figures(value.value, shown(value.value))),)

  if value.lower != none and value.upper != none {
    items.push(secondary[interval #shown(value.lower) to #shown(value.upper)])
  } else if value.lower != none {
    items.push(secondary[lower bound #shown(value.lower)])
  } else if value.upper != none {
    items.push(secondary[upper bound #shown(value.upper)])
  }

  if value.p_value != none {
    let shown = fixed(value.p_value)

    items.push(secondary(if shown.starts-with("<") { [p #shown] } else { [p = #shown] }))
  }

  stacked(items)
}

#let result(value, duration: auto) = {
  if kind-of(value) == "measurement" {
    measurement(value)
  } else if is-assessment(value) {
    emphasized(figures(value.value, in-unit(value.value, value.unit, duration: duration)))
  } else if is-failure(value) {
    not-computed
  } else {
    emphasized(figures(value, scalar(value, duration: duration)))
  }
}

// The outcome of an assessment: "passed" or "failed" (in the alert colour) on its own
// line, the condition under it after "required:".
#let check(value) = {
  if not is-assessment(value) { return [] }

  let outcome = if value.passed { [passed] } else { alert[failed] }
  let items = (outcome,)

  if value.requirement_label != "" { items.push(secondary[required: #value.requirement_label]) }

  block(breakable: false, pad(left: space.loose, stacked(items)))
}

#let body(value, title, path, within) = {
  if value.kind == "table" {
    rendered(path, "table", "table")
    tabular(value, within)
  } else if value.kind == "plot" {
    rendered(path, "plot", "plot")
    picture(value.svg, title)
  } else if value.kind == "counts" {
    counts-chart(((key: none, result: value),), path)
  } else if value.kind == "scatter" {
    scatter-chart(value, path)
  } else {
    histogram-chart(((key: none, result: value),), path)
  }
}

#let plain-of(value) = if is-assessment(value) { value.value } else { value }

#let keyed-value(value, duration: auto) = {
  if is-failure(value) { failure-text(value) } else { result(value, duration: duration) }
}

#let keyed-list(results) = {
  let checked = results.any(keyed => is-assessment(keyed.result))
  let duration = duration-unit(results.map(keyed => plain-of(keyed.result)))
  let columns = if checked { (auto, 1fr, width.check) } else { (auto, 1fr) }
  let cells = results.map(keyed => {
    let row = (secondary(scalar(keyed.key)), keyed-value(keyed.result, duration: duration))

    if checked { row.push(check(keyed.result)) }

    row
  })

  table(
    columns: columns,
    align: (left + top, right + top, left + top).slice(0, columns.len()),
    stroke: (x, y) => (bottom: lines.hairline),
    inset: (x: cell.across, y: cell.down),
    ..cells.flatten(),
  )
}

#let keyed-blocks(results, path, within) = stack(
  dir: ttb,
  spacing: space.loose,
  ..results.map(keyed => {
    let value = keyed.result

    block(width: 100%, breakable: kind-of(value) == "table", {
      secondary(scalar(keyed.key))
      v(space.tight)

      if is-wide(value) { body(value, scalar(keyed.key), path + (keyed.key,), within) } else { keyed-value(value) }
    })
  }),
)

#let failures(results) = {
  if results.len() == 0 { return }

  v(space.loose)
  stacked(results.map(keyed => failure-text(keyed.result, lead: secondary[#scalar(keyed.key):])))
}

#let same-headings(results) = {
  let first = results.first().result

  first.headings.len() > 0 and results.all(keyed => keyed.result.headings == first.headings and keyed.result.units == first.units)
}

#let note(body) = block(above: 0pt, below: space.snug, secondary(body))

#let keyed-body(entry, path, within) = {
  let results = entry.results

  if results.len() == 0 { return rendered(path, none, "none") + secondary[none] }

  if results.all(keyed => not is-wide(keyed.result)) { return rendered(path, none, "list") + keyed-list(results) }

  let computed = results.filter(keyed => not is-failure(keyed.result))
  let kinds = computed.map(keyed => kind-of(keyed.result)).dedup()

  if kinds.all(kind => kind in ("distribution", "histogram")) {
    histogram-chart(computed, path)
  } else if kinds == ("counts",) {
    counts-chart(computed, path)
  } else if kinds == ("table",) and same-headings(computed) {
    rendered(path, "table", "table")
    stacked-table(computed, within)
  } else if kinds == ("table",) {
    note[The headings differ between the keys.]
    keyed-blocks(computed, path, within)
  } else if kinds.len() == 1 {
    keyed-blocks(computed, path, within)
  } else {
    note[The results differ in kind between the keys.]
    keyed-blocks(computed, path, within)
  }

  failures(results.filter(keyed => is-failure(keyed.result)))
}

#let wide-block(heading, drawn) = (above, below) => block(
  width: 100%,
  above: above,
  below: below,
  inset: (top: space.base, bottom: space.loose),
  stroke: (bottom: lines.hairline),
  {
    block(sticky: true, below: space.snug, heading)
    drawn
  },
)

#let wide-result(item, within) = {
  let entry = item.entry
  let path = item.parent + (entry.name,)
  let heading = caption(entry, path, item.extras)

  if entry.kind == "keyed_analytic" {
    let kind = if entry.results.len() > 0 { kind-of(entry.results.first().result) }

    return (block: wide-block(heading, keyed-body(entry, path, within)), kind: kind)
  }

  if is-wide(entry.result) {
    return (block: wide-block(heading, body(entry.result, entry.title, path, within)), kind: kind-of(entry.result))
  }

  none
}

#let leaf-cells(item, checked) = {
  let entry = item.entry
  let path = item.parent + (entry.name,)
  let cells = (
    block(breakable: false, caption(entry, path, item.extras)),
    block(breakable: false, {
      rendered(path, kind-of(entry.result), "value")
      result(entry.result)
    }),
  )

  if checked { cells.push(check(entry.result)) }

  cells
}

// A group's listing: caption, value and check per row; wide results in full width.
#let listing(items, within) = {
  let checked = items.any(item => item.entry.kind == "analytic" and is-assessment(item.entry.result))
  let columns = if checked { (1fr, width.value, width.check) } else { (1fr, width.value) }
  let rows(run, sticky) = (above, below) => block(width: 100%, above: above, below: below, sticky: sticky, table(
    columns: columns,
    stroke: (x: none, top: none, bottom: lines.hairline),
    inset: (x: 0pt, y: space.base),
    align: (left + top, right + top, left + top).slice(0, columns.len()),
    ..run.map(item => leaf-cells(item, checked)).flatten(),
  ))
  let run = ()
  let parts = ()

  for item in items {
    let wide = wide-result(item, within)

    if wide == none {
      run.push(item)
      continue
    }

    if run.len() > 0 { parts.push(rows(run, wide.kind != "table")) }

    run = ()
    parts.push(wide.block)
  }

  if run.len() > 0 { parts.push(rows(run, false)) }

  for (index, part) in parts.enumerate() {
    part(if index == 0 { space.snug } else { 0pt }, if index == parts.len() - 1 { space.loose } else { 0pt })
  }
}

#let derivation-failed(entry) = {
  if entry.kind == "group" {
    entry.derivation != none and entry.derivation.failure != none
  } else {
    entry.derivations.len() > 0 and entry.derivations.all(keyed => keyed.derivation.failure != none)
  }
}

#let first-failure(entry) = {
  if entry.kind == "group" { entry.derivation.failure } else { entry.derivations.first().derivation.failure }
}

// The entries of a group as set: its listing, its own analytics and conclusions first,
// then those of its inline groups; and its groups, an inline group's groups in its place.
#let collect(entries, path, inputs) = {
  let own = ()
  let later = ()
  let groups = ()

  for entry in entries {
    let here = path + (entry.name,)
    let layout = layout-of(entry)
    let item = (entry: entry, parent: path, inputs: inputs, extras: ())

    if entry.kind in leaf-kinds {
      own.push(item)
    } else if layout == "inline" and derivation-failed(entry) {
      groups.push(item + (form: "failed"))
    } else if layout == "inline" {
      let inner = collect(entry.entries, here, entry.inputs)
      let leaves = inner.leaves
      let nested = inner.groups
      let extra = inline-extra(entry, inputs)

      if extra != none {
        let target = nested.position(found => found.form == "section")

        if target != none {
          nested.at(target).extras.insert(0, extra)
        } else if leaves.len() > 0 {
          leaves.at(0).extras.insert(0, extra)
        }
      }

      later += leaves
      groups += nested
    } else if layout == "appendix" {
      groups.push(item + (form: "appendix"))
    } else {
      groups.push(item + (form: "section"))
    }
  }

  (leaves: own + later, groups: groups)
}

// Whether a group placed across keys reports plain values only, so it is set as one table.
#let plain-members(entry) = {
  entry.kind == "keyed_group" and entry.entries.len() > 0 and entry.entries.all(member => {
    member.kind == "keyed_analytic" and member.results.all(keyed => is-plain(keyed.result))
  })
}

#let appendix-line(item) = context {
  let target = entry-label(item.parent + (item.entry.name,))

  block(above: space.base, below: space.base)[
    #item.entry.title: #link(target)[in the appendix from p. #counter(page).at(target).first()]
  ]
}

#let failed-line(item) = block(above: space.base, below: space.base, {
  failure-text(first-failure(item.entry), lead: [#item.entry.title:])
})

// A group's collected entries as set: its listing, unless the listing stands elsewhere,
// then each of its groups as a section under its heading, description and facts, as the
// line of an appendix group, or as the line of an inline group whose derivation failed.
#let render(found, depth, path, numbered, listed: true) = {
  let section(item) = {
    let entry = item.entry
    let here = item.parent + (entry.name,)

    if depth == 1 and section-breaks { pagebreak(weak: true) }

    entry-heading(depth, entry.title, here, numbered)
    description-block(entry.description)
    facts-block(facts(entry, item.inputs))

    for extra in item.extras {
      description-block(extra.description)
      facts-block(extra.facts)
    }

    if plain-members(entry) {
      rendered(here, "keyed_group", "table")
      keyed-table(entry.entries)
    } else if entry.entries.len() == 0 and not derivation-failed(entry) {
      block(width: 100%, above: 0pt, below: space.base, secondary[no entries])
    } else {
      render(collect(entry.entries, here, entry.inputs), depth + 1, here, numbered)
    }
  }

  if listed and found.leaves.len() > 0 { listing(found.leaves, path) }

  for item in found.groups {
    if item.form == "appendix" {
      appendix-line(item)
    } else if item.form == "failed" {
      failed-line(item)
    } else {
      section(item)
    }
  }
}

// The groups set as an appendix, in the order they stand, with where they stand.
#let appendix-groups(entries, path, inputs) = {
  let found = ()

  for entry in entries.filter(entry => entry.kind in ("group", "keyed_group")) {
    let here = path + (entry.name,)

    if layout-of(entry) == "appendix" {
      found.push((entry: entry, parent: path, inputs: inputs, extras: ()))
    } else {
      found += appendix-groups(entry.entries, here, entry.inputs)
    }
  }

  found
}

// "Appendix", each appendix group under the breadcrumb of its path, its keys below.
#let appendix(groups) = {
  if groups.len() == 0 { return }

  pagebreak(weak: true)
  heading(level: 1, numbering: none)[Appendix]

  for item in groups {
    let entry = item.entry
    let here = item.parent + (entry.name,)

    [#heading(level: 2, numbering: none, breadcrumb(here)) #entry-label(here)]
    description-block(entry.description)
    facts-block(facts(entry, item.inputs))

    if entry.entries.len() == 0 and not derivation-failed(entry) {
      block(width: 100%, above: 0pt, below: space.base, secondary[no entries])
    } else {
      render(collect(entry.entries, here, entry.inputs), 3, here, false)
    }
  }
}

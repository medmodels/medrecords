// Run details, only with run_details.

#import "style.typ": *
#import "numbers.typ": *
#import "references.typ": reference
#import "tables.typ": deflist, numeric-cell, sheet
#import "entries.typ": inputs-line

#let outcome-of(value) = if kind-of(value) == "failure" { "not computed" } else { "completed" }

#let derivation-of(path) = [derivation of #reference(path, ())]

// Every analytic, keyed result and derivation of the entries as (entry, outcome, seconds),
// in the order of the report.
#let timings(entries, path) = {
  let items = ()

  for entry in entries {
    let here = path + (entry.name,)

    if entry.kind == "analytic" {
      items.push((reference(here, ()), outcome-of(entry.result), entry.duration))
    } else if entry.kind == "keyed_analytic" {
      items += entry.results.map(keyed => (reference(here + (keyed.key,), ()), outcome-of(keyed.result), keyed.duration))
    } else if entry.kind == "group" {
      if entry.derivation != none {
        items.push((derivation-of(here), outcome-of(entry.derivation.failure), entry.derivation.duration))
      }

      items += timings(entry.entries, here)
    } else {
      items += entry.derivations.map(keyed => (
        derivation-of(here + (keyed.key,)),
        outcome-of(keyed.derivation.failure),
        keyed.derivation.duration,
      ))
      items += timings(entry.entries, here)
    }
  }

  items
}

// "Run details": when the run started, how long it took, the software and its inputs;
// then every entry with its outcome and duration, the slowest first.
#let run-details-page() = {
  let items = timings(report.entries, ()).sorted(key: item => -item.at(2))
  let facts = (
    ("Started", moment(report.started_at)),
    ("Duration", seconds(report.duration)),
    ("Software", "medrecords " + options.version),
  )

  if report.inputs.len() > 0 { facts.push(("Inputs", inputs-line(report.inputs))) }

  pagebreak(weak: true)
  heading(level: 1, numbering: none)[Run details]
  block(width: 100%, above: space.base, below: space.loose, deflist(facts))

  let rows = (([All entries], [], seconds(report.duration)),) + items.map(((entry, outcome, duration)) => (entry, outcome, seconds(duration)))

  sheet(
    (1fr, auto, auto),
    (left, left, right),
    ("entry", "outcome", "duration"),
    rows.map(((entry, outcome, duration)) => (entry, outcome, numeric-cell(duration))).flatten(),
  )
}

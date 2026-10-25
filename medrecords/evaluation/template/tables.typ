// Tables and sheets.

#import "style.typ": *
#import "numbers.typ": *
#import "references.typ": reference

#let numeric-cell(body) = text(number-width: "tabular", body)

// One table style: a tinted header row repeated on every page, hairlines between the
// body rows, in the small face.
#let sheet(columns, aligns, headings, cells) = {
  show table.cell.where(y: 0): set text(weight: "semibold", fill: palette.navy)
  set text(size: size.small)

  table(
    columns: columns,
    align: aligns.map(side => side + top),
    fill: (x, y) => if y == 0 { palette.tint } else { none },
    stroke: (x, y) => if y > 1 { (top: lines.hairline) },
    inset: (x: cell.across, y: cell.down),
    table.header(..headings, repeat: true),
    ..cells,
  )
}

#let deflist(items) = grid(
  columns: (auto, 1fr),
  column-gutter: space.loose,
  row-gutter: space.tight,
  align: (left + top, left + top),
  ..items.map(((name, value)) => (text(fill: palette.muted, name), value)).flatten(),
)

// A block that breaks across pages only when it is taller than a page.
#let kept(body) = layout(available => block(breakable: measure(body, width: available.width).height > available.height, body))

#let is-path(value) = kind-of(value) == "path"

#let column-of(rows, index) = rows.map(row => row.at(index))

// A column is numeric when every value it holds is a number.
#let numeric-columns(count, rows) = range(count).map(index => {
  let values = column-of(rows, index).filter(value => value != none and kind-of(value) != "failure")

  values.len() > 0 and values.all(numeric)
})

// Numeric columns are set to the right, as wide as their numbers and heading; the
// columns of text share the rest of the width.
#let column-aligns(numerics) = numerics.map(is-numeric => if is-numeric { right } else { left })

#let column-widths(numerics) = numerics.map(is-numeric => if is-numeric { auto } else { 1fr })

// One cell of a table: a path as a breadcrumb, a null as an empty cell.
#let table-cell(value, unit, duration, places, within) = {
  if is-path(value) { return reference(value.names, within) }

  let shown = in-unit(value, unit, duration: duration, places: places, empty: [], aligned: true)

  if numeric(value) { numeric-cell(shown) } else { shown }
}

#let row-cells(value, rows, row, within) = {
  let count = value.headings.len()
  let durations = range(count).map(index => duration-unit(column-of(rows, index)))
  let places = range(count).map(index => column-decimals(column-of(rows, index)))

  row.enumerate().map(((index, item)) => table-cell(item, value.units.at(index), durations.at(index), places.at(index), within))
}

#let omitted-line(omitted) = {
  if omitted > 0 { block(above: space.tight, below: 0pt, secondary[and #counted(omitted, "more row")]) }
}

#let printed-rows(value) = {
  if value.printed_rows == none { value.rows } else { value.rows.slice(0, calc.min(value.printed_rows, value.rows.len())) }
}

// A Table: path cells as breadcrumbs relative to the section it stands in, "none"
// without rows, "and N more rows" when cut to its printed rows. Number formats are
// chosen over every row, so a cut table formats its numbers as the full one does.
#let tabular(value, within) = {
  if value.headings.len() == 0 or value.rows.len() == 0 { return secondary[none] }

  let rows = printed-rows(value)
  let headings = value.headings.map(str)
  let cells = rows.map(row => row-cells(value, value.rows, row, within)).flatten()

  let numerics = numeric-columns(headings.len(), rows)

  sheet(column-widths(numerics), column-aligns(numerics), headings, cells)
  omitted-line(value.rows.len() - rows.len())
}

// Keyed tables with equal headings as one table, the key in the first column; each
// key cut to its printed rows, with a row saying how many of that key follow.
#let stacked-table(results, within) = {
  let first = results.first().result
  let rows = results.map(keyed => keyed.result.rows).sum(default: ())
  let headings = ("",) + first.headings.map(str)
  let omitted-row(keyed, printed) = {
    let omitted = keyed.result.rows.len() - printed.len()

    if omitted > 0 { (table.cell(colspan: headings.len(), secondary[and #counted(omitted, "more row") of #scalar(keyed.key)]),) } else { () }
  }
  let cells = results
    .map(keyed => {
      let printed = printed-rows(keyed.result)

      printed.map(row => (scalar(keyed.key),) + row-cells(first, rows, row, within)).flatten() + omitted-row(keyed, printed)
    })
    .flatten()

  let numerics = (false,) + numeric-columns(first.headings.len(), rows)

  sheet(column-widths(numerics), column-aligns(numerics), headings, cells)
}

// A section placed across keys whose members report plain values: a row per key, a
// column per member titled by the member's title.
#let keyed-table(members) = {
  let keys = members.map(member => member.results.map(keyed => keyed.key)).flatten().dedup()
  let headings = ("",) + members.map(member => member.title)
  let found(member, key) = member.results.find(keyed => keyed.key == key)
  let rows = keys.map(key => members.map(member => {
    let keyed = found(member, key)

    if keyed == none { none } else { keyed.result }
  }))
  let places = range(members.len()).map(index => column-decimals(column-of(rows, index)))
  let durations = range(members.len()).map(index => duration-unit(column-of(rows, index)))
  let shown(value, index) = {
    if kind-of(value) == "failure" { return secondary[not computed] }

    let body = scalar(
      value,
      duration: durations.at(index),
      places: places.at(index),
      empty: [],
      aligned: true,
    )

    if numeric(value) { numeric-cell(body) } else { body }
  }
  let cells = keys
    .zip(rows)
    .map(((key, row)) => (scalar(key),) + row.enumerate().map(((index, value)) => shown(value, index)))
    .flatten()

  let numerics = (false,) + numeric-columns(members.len(), rows)

  sheet(column-widths(numerics), column-aligns(numerics), headings, cells)
}

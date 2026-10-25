// Tables and sheets.

#import "style.typ": *
#import "numbers.typ": *
#import "references.typ": reference

#let table-rows = options.table_rows

#let numeric-cell(body) = text(number-width: "tabular", body)

// One table style: a tinted header row repeated on every page, hairlines between rows.
#let sheet(columns, aligns, headings, cells) = {
  show table.cell.where(y: 0): set text(weight: "semibold", fill: palette.navy)

  table(
    columns: columns,
    align: aligns.map(side => side + top),
    fill: (x, y) => if y == 0 { palette.tint } else { none },
    stroke: (x, y) => if y == 0 { none } else { (bottom: lines.hairline) },
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

#let fitted(build) = layout(available => {
  let natural = measure(build(size.body)).width

  if natural <= available.width { return build(size.body) }

  let smaller = size.body * (available.width / natural)
  let narrowed = measure(build(smaller)).width

  if narrowed <= available.width { return build(smaller) }

  build(smaller * (available.width / narrowed))
})

#let is-path(value) = kind-of(value) == "path"

#let cell-length(value) = {
  if type(value) == str { value.clusters().len() } else if is-path(value) {
    value.names.map(name => str(name).clusters().len() + 3).sum(default: 0)
  } else { 0 }
}

#let column-of(rows, index) = rows.map(row => row.at(index))

#let column-aligns(count, rows) = range(count).map(index => {
  let values = column-of(rows, index).filter(value => value != none and kind-of(value) != "failure")

  if values.len() > 0 and numeric(values.first()) { right } else { left }
})

#let column-widths(headings, rows) = range(headings.len()).map(index => {
  let longest = calc.max(str(headings.at(index)).clusters().len(), ..column-of(rows, index).map(cell-length))

  if longest > longest-cell { width.cell } else { auto }
})

// One cell of a table: a path as a breadcrumb, a null as an empty cell.
#let table-cell(value, unit, duration, places, within) = {
  if is-path(value) { return reference(value.names, within) }

  let shown = in-unit(value, unit, duration: duration, places: places, empty: [])

  if numeric(value) { numeric-cell(shown) } else { shown }
}

#let row-cells(value, rows, row, within) = {
  let count = value.headings.len()
  let durations = range(count).map(index => duration-unit(column-of(rows, index)))
  let places = range(count).map(index => column-decimals(column-of(rows, index)))

  row.enumerate().map(((index, item)) => table-cell(item, value.units.at(index), durations.at(index), places.at(index), within))
}

#let shrunk(build) = block(above: 0pt, below: 0pt, fitted(text-size => text(size: text-size, build())))

#let omitted-line(omitted) = {
  if omitted > 0 { block(above: space.tight, below: 0pt, secondary[and #counted(omitted, "more row")]) }
}

// A Table: path cells as breadcrumbs relative to the section it stands in, "none"
// without rows, "and N more rows" when cut to table_rows.
#let tabular(value, within) = {
  if value.headings.len() == 0 or value.rows.len() == 0 { return secondary[none] }

  let rows = value.rows
  let omitted = 0

  if table-rows != none and rows.len() > table-rows {
    omitted = rows.len() - table-rows
    rows = rows.slice(0, table-rows)
  }

  let headings = value.headings.map(str)
  let cells = rows.map(row => row-cells(value, rows, row, within)).flatten()

  shrunk(() => sheet(column-widths(headings, rows), column-aligns(headings.len(), rows), headings, cells))
  omitted-line(omitted)
}

// Keyed tables with equal headings as one table, the key in the first column.
#let stacked-table(results, within) = {
  let first = results.first().result
  let rows = results.map(keyed => keyed.result.rows).sum(default: ())
  let headings = ("",) + first.headings.map(str)
  let cells = results
    .map(keyed => keyed.result.rows.map(row => (scalar(keyed.key),) + row-cells(first, rows, row, within)))
    .flatten()

  shrunk(() => sheet(headings.len() * (auto,), (left,) + column-aligns(first.headings.len(), rows), headings, cells))
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

    let body = scalar(value, duration: durations.at(index), places: places.at(index), empty: [])

    if numeric(value) { numeric-cell(body) } else { body }
  }
  let cells = keys
    .zip(rows)
    .map(((key, row)) => (scalar(key),) + row.enumerate().map(((index, value)) => shown(value, index)))
    .flatten()

  shrunk(() => sheet(headings.len() * (auto,), (left,) + column-aligns(members.len(), rows), headings, cells))
}

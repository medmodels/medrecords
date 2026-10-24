#let report = json(bytes(sys.inputs.report))
#let logo = sys.inputs.logo
#let options = json(bytes(sys.inputs.options))

#let kind = options.kind
#let run-details = options.run_details
#let section-breaks = options.section_breaks
#let parameter-lines = options.parameter_lines
#let failure-details = options.failure_details

#let palette = (
  navy: rgb("#03045E"),
  tint: rgb("#F0F9FC"),
  ink: rgb("#0F172A"),
  muted: rgb("#64748B"),
  line: rgb("#E2E8F0"),
  alert: rgb("#B91C1C"),
  series: (rgb("#03045E"), rgb("#00B4D8"), rgb("#0077B6"), rgb("#90E0EF")),
)

#let size = (
  title: 24pt,
  section: 16pt,
  subsection: 13pt,
  minor: 11pt,
  body: 10pt,
  small: 8.5pt,
  tiny: 8pt,
)

#let space = (
  hair: 2pt,
  tight: 4pt,
  snug: 6pt,
  base: 8pt,
  loose: 12pt,
  wide: 24pt,
)

#let width = (
  value: 4cm,
  check: 5cm,
  label: 2.6cm,
  cell: 6cm,
  wordmark: 6cm,
  running-wordmark: 2.4cm,
)

#let lines = (
  hairline: 0.5pt + palette.line,
  rule: 0.5pt + palette.ink,
  axis: 0.5pt + palette.muted,
)

#let fonts = (
  text: "Inter",
  mono: "DejaVu Sans Mono",
)

#let chart = (
  height: 80pt,
  tallest: 420pt,
)

#let cell = (
  across: 0.8em,
  down: 0.6em,
)

#let decimals = 3

#let smallest = 0.001

#let most-decimals = 12

#let largest = 1000000

#let tiniest = 0.000000000001

#let longest-word = 25

#let longest-cell = 40

#let tallest-caption = 10cm

#let word-piece = 12

#let heading-steps = (
  (size: size.section),
  (size: size.subsection),
  (size: size.minor),
  (size: size.body),
  (size: size.body, style: "italic"),
)

#let seconds-per = (
  microsecond: 0.000001,
  minute: 60,
  hour: 3600,
  day: 86400,
)

#let company = options.company

#let wide-kinds = ("table", "plot", "distribution", "histogram", "counts")

// Bars are drawn from this many categories or bins on; fewer are printed as a sheet.
#let fewest-bars = 2

// Count labels over histogram bars are dropped below this bar width.
#let narrowest-bar = 14pt

// A sheet taller than this share of the page may break across pages.
#let unbroken = 50%


#let digits-for(value) = {
  let magnitude = calc.abs(value)

  if magnitude == 0 or magnitude >= smallest { return decimals }

  calc.min(decimals - calc.floor(calc.log(magnitude)) - 1, most-decimals)
}

#let compact(number) = {
  if number == 0 { return "0" }

  let exponent = calc.floor(calc.log(calc.abs(number)))
  let half = calc.quo(exponent, 2)
  let mantissa = calc.round(
    number / calc.pow(10.0, half) / calc.pow(10.0, exponent - half),
    digits: 2,
  )

  if calc.abs(mantissa) >= 10 {
    mantissa = mantissa / 10
    exponent += 1
  }

  str(mantissa) + "e" + str(exponent)
}

#let padded(value, places) = {
  let shown = str(calc.round(value, digits: places))

  if not shown.contains(".") { return shown + "." + "0" * places }

  let (whole, fraction) = shown.split(".")

  whole + "." + fraction + "0" * calc.max(0, places - fraction.len())
}

#let fixed(value) = {
  if calc.abs(value) >= largest { return compact(value) }

  if calc.abs(value) < tiniest and value != 0 {
    return (if value < 0 { "> −" } else { "< " }) + compact(tiniest)
  }

  padded(value, digits-for(value))
}

#let short(number, step, exponential) = {
  if exponential {
    compact(number)
  } else if calc.rem(number, 1) == 0 {
    str(int(number))
  } else {
    str(calc.round(number, digits: digits-for(step)))
  }
}

#let unit-for(magnitude) = {
  if magnitude < 1 { "ms" } else if magnitude < seconds-per.minute { "s" } else if magnitude < seconds-per.hour { "min" } else if magnitude < seconds-per.day { "h" } else { "d" }
}

#let per-unit = (ms: 0.001, s: 1, min: seconds-per.minute, h: seconds-per.hour, d: seconds-per.day)

#let seconds(duration, unit: auto) = {
  let sign = if duration < 0 { "−" } else { "" }
  let magnitude = calc.abs(duration)
  let chosen = if unit == auto { unit-for(magnitude) } else { unit }
  let scaled = magnitude / per-unit.at(chosen)

  if magnitude != 0 and scaled < 0.05 { return sign + "< 0.1 " + chosen }

  sign + padded(scaled, 1) + " " + chosen
}

#let moment(stamp) = {
  let shown = stamp.slice(0, 10) + " " + stamp.slice(11, 16)
  let tail = stamp.slice(19)
  let signs = ("+", "-")
  let offset = if tail.ends-with("Z") {
    "+00:00"
  } else if tail.len() >= 6 and tail.slice(-6, -5) in signs {
    tail.slice(-6)
  } else {
    ""
  }

  if offset == "" { shown } else if offset == "+00:00" { shown + " UTC" } else {
    shown + " " + offset
  }
}

#let kind-of(value) = if type(value) == dictionary { value.at("kind", default: none) }

#let is-duration(value) = kind-of(value) == "timedelta"

#let duration-seconds(value) = value.days * seconds-per.day + value.seconds + value.microseconds * seconds-per.microsecond

#let duration-unit(cells) = {
  let durations = cells.filter(is-duration)

  if durations.len() == 0 { return auto }

  unit-for(calc.max(..durations.map(cell => calc.abs(duration-seconds(cell)))))
}

#let numeric(value) = {
  type(value) in (int, float) or kind-of(value) in ("timedelta", "float")
}

#let scalar(value, duration: auto) = {
  if value == none {
    text(fill: palette.muted)[none]
  } else if type(value) == bool {
    if value { "true" } else { "false" }
  } else if type(value) == float {
    fixed(value)
  } else if kind-of(value) == "timedelta" {
    seconds(duration-seconds(value), unit: duration)
  } else if kind-of(value) == "datetime" {
    let (date, time) = value.value.slice(0, 19).split("T")

    if time == "00:00:00" { date } else { date + " " + time }
  } else if kind-of(value) == "float" {
    if value.value == "nan" { "not a number" } else if value.value == "inf" {
      "infinity"
    } else { "minus infinity" }
  } else {
    str(value)
  }
}

#let listed(value) = {
  if type(value) == array {
    "[" + value.map(scalar).join(", ") + "]"
  } else {
    scalar(value)
  }
}


#let percent(share) = padded(share * 100, 1) + "%"

#let points(difference) = padded(difference * 100, 1) + " pp"

#let in-unit(cell, unit, duration: auto) = {
  if unit == "share" and type(cell) in (int, float) {
    percent(cell)
  } else if unit == "points" and type(cell) in (int, float) {
    points(cell)
  } else {
    scalar(cell, duration: duration)
  }
}

#let column-durations(value, rows) = range(value.headings.len()).map(index => duration-unit(rows.map(row => row.at(index))))

#let column-cells(value, row) = {
  let units = value.units
  let durations = column-durations(value, value.rows)

  row.enumerate().map(((index, cell)) => in-unit(cell, units.at(index), duration: durations.at(index)))
}

#let column-aligns(value, rows) = range(value.headings.len()).map(index => {
  let cells = rows.map(row => row.at(index)).filter(cell => cell != none)

  if cells.len() > 0 and numeric(cells.first()) { right } else { left }
})

#let secondary(body) = text(size: size.small, fill: palette.muted, body)

#let mono(body) = text(font: fonts.mono, size: size.tiny, fill: palette.muted, body)

#let emphasized(body) = strong(body)

#let alert(body) = strong(text(fill: palette.alert, body))

#let stacked(items) = stack(dir: ttb, spacing: space.tight, ..items)

#let pairs(mapping) = {
  mono(mapping.pairs().map(((name, value)) => [#name = #listed(value)]).join([, ]))
}


#let sheet(columns, aligns, headings, cells) = {
  set text(number-width: "tabular")
  show table.cell.where(y: 0): set text(weight: "semibold", fill: palette.navy)

  table(
    columns: columns,
    align: aligns.map(side => side + top),
    fill: (x, y) => if y == 0 { palette.tint } else { none },
    stroke: (x, y) => if y == 0 { none } else { (bottom: lines.hairline) },
    inset: (x: cell.across, y: cell.down),
    table.header(..headings),
    ..cells,
  )
}

#let fitted(build) = layout(available => {
  let natural = measure(build(size.body)).width

  if natural <= available.width { return build(size.body) }

  let smaller = size.body * (available.width / natural)
  let narrowed = measure(build(smaller)).width

  if narrowed <= available.width { return build(smaller) }

  build(smaller * (available.width / narrowed))
})

#let deflist(items) = grid(
  columns: (width.label, 1fr),
  inset: (x: 0pt, y: space.hair),
  align: (left + top, left + top),
  ..items.map(((name, value)) => (text(fill: palette.muted, name), value)).flatten(),
)


#let is-wide(entry) = kind-of(entry.result) in wide-kinds

#let is-assessment(value) = kind-of(value) == "assessment"

#let is-failure(value) = kind-of(value) == "failure"

#let caption(entry) = {
  let items = (emphasized(entry.title),)

  if entry.description != none {
    items.push(secondary(entry.description))
  }

  if parameter-lines and entry.parameters.len() > 0 {
    items.push(pairs(entry.parameters))
  }

  if entry.kind == "analytic" and is-failure(entry.result) and failure-details {
    items.push(secondary[
      #entry.result.exception_type: #entry.result.message
    ])
  }

  block(stacked(items))
}

#let measurement(value) = {
  let shown(number) = in-unit(number, value.unit)
  let items = (emphasized(shown(value.value)),)

  if value.lower != none and value.upper != none {
    items.push(secondary[interval #shown(value.lower) to #shown(value.upper)])
  } else if value.lower != none {
    items.push(secondary[lower bound #shown(value.lower)])
  } else if value.upper != none {
    items.push(secondary[upper bound #shown(value.upper)])
  }

  if value.p_value != none {
    let shown = fixed(value.p_value)

    if shown.starts-with("<") {
      items.push(secondary[p #shown])
    } else {
      items.push(secondary[p = #shown])
    }
  }

  stacked(items)
}

#let failed = {
  if failure-details { alert[error] } else { secondary[not computed] }
}

#let result(value, duration: auto) = {
  if kind-of(value) == "measurement" {
    measurement(value)
  } else if is-assessment(value) {
    emphasized(in-unit(value.value, value.unit, duration: duration))
  } else if is-failure(value) {
    failed
  } else {
    emphasized(scalar(value, duration: duration))
  }
}

#let check(value) = {
  let shown = if is-assessment(value) {
    let label = if value.requirement_label == "" { [] } else {
      [ (#value.requirement_label)]
    }

    if value.passed { [passed#label] } else { [#alert[failed]#label] }
  } else {
    []
  }

  block(breakable: false, pad(left: space.loose, shown))
}


#let tabular(value) = {
  let count = value.headings.len()

  if count == 0 {
    return secondary[empty table]
  }

  if value.rows.len() == 0 {
    return secondary[no rows]
  }

  let aligns = column-aligns(value, value.rows)
  let columns = range(count).map(index => {
    let lengths = value.rows.map(row => {
      let cell = row.at(index)

      if type(cell) == str { cell.clusters().len() } else { 0 }
    })

    if calc.max(str(value.headings.at(index)).clusters().len(), ..lengths) > longest-cell {
      width.cell
    } else {
      auto
    }
  })

  block(
    above: 0pt,
    below: 0pt,
    fitted(text-size => text(
      size: text-size,
      sheet(columns, aligns, value.headings.map(str), value.rows.map(row => column-cells(value, row)).flatten()),
    )),
  )
}

#let counted(number, noun) = str(number) + " " + noun + (if number == 1 { "" } else { "s" })

#let mark(body) = text(size: size.tiny, fill: palette.muted, body)

#let bins-of(value) = {
  let binned = if value.kind == "distribution" { value.histogram } else { value }

  binned.edges.windows(2).zip(binned.counts).map(((pair, count)) => (
    lower: pair.first(),
    upper: pair.last(),
    count: count,
  ))
}

#let total-of(value) = {
  if value.kind == "distribution" {
    value.statistics.count
  } else if value.kind == "histogram" {
    value.counts.sum(default: 0) + value.below_count + value.above_count
  } else {
    value.total
  }
}

#let remainder-of(value) = value.total - value.counts.map(item => item.count).sum(default: 0)

#let labeller(bins) = {
  let step = bins.first().upper - bins.first().lower
  let exponential = bins.any(bin => {
    let magnitude = calc.max(calc.abs(bin.lower), calc.abs(bin.upper))

    magnitude >= largest or (magnitude != 0 and magnitude < smallest)
  })

  number => mark(short(number, step, exponential))
}

#let gutter-for(count, available) = calc.min(space.snug, available / count / 4)

#let bars(series, available, labelled) = {
  let count = series.first().labels.len()
  let tallest = calc.max(..series.map(one => calc.max(..one.shares)))
  let tower(one, index) = {
    let height = if tallest == 0 { 0pt } else { chart.height * one.shares.at(index) / tallest }
    let parts = (rect(width: 100%, height: height, fill: one.colour),)

    if labelled { parts.insert(0, align(center, mark(one.labels.at(index)))) }

    stack(dir: ttb, spacing: space.tight, ..parts)
  }
  let bar(index) = grid(
    columns: series.len() * (1fr,),
    column-gutter: space.hair,
    align: bottom,
    ..series.map(one => tower(one, index)),
  )
  let headroom = if labelled { size.tiny + space.snug } else { 0pt }

  box(
    width: 100%,
    height: chart.height + headroom,
    grid(
      columns: count * (1fr,),
      column-gutter: gutter-for(count, available),
      align: bottom,
      ..range(count).map(bar),
    ),
  )
}

#let axis(labels, available, trailing: none) = {
  line(length: 100%, stroke: lines.axis)
  v(space.hair)
  block(width: 100%, {
    if trailing != none { place(top + right, trailing) }

    grid(columns: labels.len() * (1fr,), column-gutter: gutter-for(labels.len(), available), ..labels)
  })
}

#let edges-axis(bins, marked, available) = {
  let widest = calc.max(..bins.map(bin => measure(marked(bin.lower)).width))
  let every = calc.max(1, calc.ceil(widest * bins.len() / available))
  let shown(index) = calc.rem(index, every) == 0 and (every == 1 or index < bins.len() - every)
  let labels = bins.enumerate().map(((index, bin)) => if shown(index) { marked(bin.lower) })

  axis(labels, available, trailing: marked(bins.last().upper))
}

#let outside(value, marked, prefix) = {
  if value.kind != "histogram" or value.below_count + value.above_count == 0 { return }

  v(space.tight)
  secondary[
    #prefix#counted(value.below_count, "value") below #marked(value.edges.first()),
    #counted(value.above_count, "value") above #marked(value.edges.last())
  ]
}

#let narrow-note = secondary[counts not shown: the bars are too narrow]

#let rendered(path, kind, picture, labelled: none) = [
  #metadata((path: path, kind: kind, picture: picture, labelled: labelled)) <rendering>
]

#let statistics-headings = ("n", "mean", "std", "min", "q1", "median", "q3", "max")

#let order-statistics(statistics) = (
  statistics.minimum,
  statistics.lower_quartile,
  statistics.median,
  statistics.upper_quartile,
  statistics.maximum,
)

#let exact-digits(numbers) = {
  let found = range(decimals + 1).find(digits => numbers.all(number => calc.round(number, digits: digits) == number))

  if found == none { decimals } else { found }
}

#let exactly(number, digits) = if digits == 0 { str(int(number)) } else { padded(number, digits) }

#let statistics-cells(statistics, digits) = (
  (str(statistics.count), fixed(statistics.mean), fixed(statistics.standard_deviation))
    + order-statistics(statistics).map(number => exactly(number, digits))
)

#let figures(statistics) = sheet(
  8 * (1fr,),
  8 * (right,),
  statistics-headings,
  statistics-cells(statistics, exact-digits(order-statistics(statistics))),
)

#let keyed-figures(results) = {
  let described = results.filter(keyed => keyed.result.statistics != none)

  if described.len() == 0 { return }

  let digits = exact-digits(described.map(keyed => order-statistics(keyed.result.statistics)).flatten())

  v(space.loose)
  sheet(
    (width.label,) + 8 * (1fr,),
    (left,) + 8 * (right,),
    ("",) + statistics-headings,
    described.map(keyed => (scalar(keyed.key),) + statistics-cells(keyed.result.statistics, digits)).flatten(),
  )
}

#let bins-sheet(bins, marked) = sheet(
  (1fr, 1fr, width.label),
  (right, right, right),
  ("from", "to", "count"),
  bins.map(bin => (marked(bin.lower), marked(bin.upper), str(bin.count))).flatten(),
)

#let histogram(value, path) = {
  let bins = bins-of(value)
  let total = total-of(value)

  if total == 0 {
    return rendered(path, value.kind, "none") + secondary[no values]
  }

  let marked = labeller(bins)
  let counts = bins.map(bin => bin.count)
  let series = ((shares: counts.map(count => count / total), labels: counts.map(str), colour: palette.navy),)

  layout(available => block(width: 100%, breakable: false, {
    if bins.len() < fewest-bars {
      rendered(path, value.kind, "sheet")
      bins-sheet(bins, marked)
    } else {
      let labelled = available.width / bins.len() >= narrowest-bar

      rendered(path, value.kind, "bars", labelled: labelled)
      bars(series, available.width, labelled)
      edges-axis(bins, marked, available.width)

      if not labelled {
        v(space.tight)
        narrow-note
      }
    }

    outside(value, marked, [])

    if value.statistics == none {
      v(space.tight)
      secondary[#counted(total, "value")]
    } else {
      v(space.loose)
      figures(value.statistics)
    }
  }))
}

#let counts-sheet(value) = {
  let rows = value.counts.map(item => (scalar(item.value), str(item.count), percent(item.count / value.total)))
  let remainder = remainder-of(value)

  if remainder > 0 {
    rows.push((secondary[other values], str(remainder), percent(remainder / value.total)))
  }

  sheet((1fr, width.label, width.label), (left, right, right), ("value", "count", "share"), rows.flatten())
}

#let category-labels(categories) = categories.map(category => align(center, mark(scalar(category))))

#let labels-fit(labels, slot) = labels.all(label => measure(label).width <= slot)

#let counts-picture(categories, series, available) = {
  if categories.len() < fewest-bars { return false }

  let slot = available / (categories.len() * series.len())
  let percent-labels = series.map(one => one.labels.map(mark)).flatten()

  labels-fit(category-labels(categories) + percent-labels, slot)
}

#let counts(value, path) = {
  if value.total == 0 {
    return rendered(path, "counts", "none") + secondary[no values]
  }

  let categories = value.counts.map(item => item.value)
  let shares = value.counts.map(item => item.count / value.total)
  let series = ((shares: shares, labels: shares.map(percent), colour: palette.navy),)

  layout(available => block(width: 100%, breakable: false, {
    if counts-picture(categories, series, available.width) {
      rendered(path, "counts", "bars", labelled: true)
      bars(series, available.width, true)
      axis(category-labels(categories), available.width)
      v(space.loose)
    } else {
      rendered(path, "counts", "sheet")
    }

    counts-sheet(value)
  }))
}

#let picture(svg, description) = {
  let drawing = image(bytes(svg), format: "svg")

  layout(area => {
    let natural = measure(drawing)
    let ratio = calc.min(
      1.0,
      area.width / natural.width,
      chart.tallest / natural.height,
    )

    image(
      bytes(svg),
      format: "svg",
      width: natural.width * ratio,
      alt: description,
    )
  })
}

#let body(value, title, path) = {
  if value.kind == "table" {
    rendered(path, "table", "table")
    tabular(value)
  } else if value.kind == "plot" {
    rendered(path, "plot", "plot")
    picture(value.svg, title)
  } else if value.kind == "counts" {
    counts(value, path)
  } else {
    histogram(value, path)
  }
}


#let leaf-kinds = ("analytic", "keyed_analytic")

#let section-kinds = ("group", "keyed_group")

#let narrow(value) = not is-wide((result: value))

#let series-colour(index) = palette.series.at(calc.rem(index, palette.series.len()))

#let keyed-value(value, duration: auto) = {
  if is-failure(value) and failure-details {
    stacked((failed, secondary[#value.exception_type: #value.message]))
  } else {
    result(value, duration: duration)
  }
}

#let plain-of(value) = if is-assessment(value) { value.value } else { value }

#let keyed-list(results) = {
  let checked = results.any(keyed => is-assessment(keyed.result))
  let duration = duration-unit(results.map(keyed => plain-of(keyed.result)))
  let columns = if checked { (width.label, 1fr, width.check) } else { (width.label, 1fr) }
  let cells = results.map(keyed => {
    let row = (secondary(scalar(keyed.key)), keyed-value(keyed.result, duration: duration))

    if checked { row.push(check(keyed.result)) }

    row
  })

  set text(number-width: "tabular")

  table(
    columns: columns,
    align: (left + top, right + top, left + top).slice(0, columns.len()),
    stroke: (x, y) => (bottom: lines.hairline),
    inset: (x: cell.across, y: cell.down),
    ..cells.flatten(),
  )
}

#let stacked-table(results) = {
  let first = results.first().result
  let count = first.headings.len() + 1
  let cells = results.map(keyed => keyed.result.rows.map(row => (scalar(keyed.key),) + column-cells(first, row))).flatten()
  let aligns = (left,) + column-aligns(first, results.map(keyed => keyed.result.rows).sum(default: ()))

  block(
    above: 0pt,
    below: 0pt,
    fitted(text-size => text(
      size: text-size,
      sheet(count * (auto,), aligns, ("",) + first.headings.map(str), cells),
    )),
  )
}

#let totals(results, swatches) = {
  let items = results.enumerate().map(((index, keyed)) => [
    #if swatches [#box(width: 0.8em, height: 0.8em, fill: series-colour(index))#h(space.tight)]
    #scalar(keyed.key) (n = #str(total-of(keyed.result)))
  ])

  secondary(items.join(h(space.loose)))
}

#let keyed-series(results, counts-of, labels-of) = results.enumerate().map(((index, keyed)) => {
  let total = total-of(keyed.result)
  let counts = counts-of(keyed.result)
  let shares = counts.map(count => if total == 0 { 0 } else { count / total })

  (shares: shares, labels: labels-of(counts, shares), colour: series-colour(index))
})

#let grouped-histogram(results, path) = {
  let first = results.first().result
  let bins = bins-of(first)
  let series = keyed-series(results, value => bins-of(value).map(bin => bin.count), (counts, shares) => counts.map(str))
  let marked = labeller(bins)

  layout(available => block(width: 100%, breakable: false, {
    if bins.len() < fewest-bars {
      rendered(path, first.kind, "sheet")
      totals(results, false)
      v(space.snug)
      stacked(results.map(keyed => [#secondary(scalar(keyed.key)) #v(space.hair) #bins-sheet(bins-of(keyed.result), marked)]))
    } else {
      let labelled = available.width / (bins.len() * series.len()) >= narrowest-bar

      rendered(path, first.kind, "bars", labelled: labelled)
      totals(results, true)
      v(space.snug)
      bars(series, available.width, labelled)
      edges-axis(bins, marked, available.width)

      if not labelled {
        v(space.tight)
        narrow-note
      }
    }

    for keyed in results {
      outside(keyed.result, marked, [#scalar(keyed.key): ])
    }

    keyed-figures(results)
  }))
}

#let count-of(value, category) = {
  let found = value.counts.find(item => item.value == category)

  if found == none { 0 } else { found.count }
}

#let joined-counts(results, categories) = {
  let share(value, count) = if value.total == 0 { "" } else { percent(count / value.total) }
  let headings = ("value",) + results.map(keyed => ([#scalar(keyed.key) count], [#scalar(keyed.key) share])).flatten()
  let rows = categories.map(category => (
    (scalar(category),) + results.map(keyed => {
      let count = count-of(keyed.result, category)

      (str(count), share(keyed.result, count))
    }).flatten()
  ))

  if results.any(keyed => remainder-of(keyed.result) > 0) {
    rows.push((secondary[other values],) + results.map(keyed => {
      let remainder = remainder-of(keyed.result)

      (str(remainder), share(keyed.result, remainder))
    }).flatten())
  }

  block(
    above: 0pt,
    below: 0pt,
    fitted(text-size => text(
      size: text-size,
      sheet((1fr,) + 2 * results.len() * (auto,), (left,) + 2 * results.len() * (right,), headings, rows.flatten()),
    )),
  )
}

#let grouped-counts(results, path) = {
  let categories = results.map(keyed => keyed.result.counts.map(item => item.value)).flatten().dedup()

  if results.all(keyed => keyed.result.total == 0) {
    return rendered(path, "counts", "none") + block(width: 100%, { totals(results, false); v(space.snug); secondary[no values] })
  }

  let series = keyed-series(results, value => categories.map(category => count-of(value, category)), (counts, shares) => shares.map(percent))

  layout(available => block(width: 100%, breakable: false, {
    if categories.len() > 0 and counts-picture(categories, series, available.width) {
      rendered(path, "counts", "bars", labelled: true)
      totals(results, true)
      v(space.snug)
      bars(series, available.width, true)
      axis(category-labels(categories), available.width)
      v(space.loose)
    } else {
      rendered(path, "counts", "sheet")
      totals(results, false)
      v(space.snug)
    }

    joined-counts(results, categories)
  }))
}

#let keyed-blocks(results, path) = {
  stack(
    dir: ttb,
    spacing: space.loose,
    ..results.map(keyed => {
      let value = keyed.result

      block(width: 100%, breakable: not narrow(value), {
        secondary(scalar(keyed.key))
        v(space.tight)

        if narrow(value) { keyed-value(value) } else { body(value, scalar(keyed.key), path + (keyed.key,)) }
      })
    }),
  )
}

#let failures(results) = {
  if results.len() == 0 { return }

  v(space.loose)
  stacked(results.map(keyed => {
    secondary(scalar(keyed.key))
    v(space.tight)
    keyed-value(keyed.result)
  }))
}

#let same-edges(results) = results.all(keyed => keyed.result.edges == results.first().result.edges)

#let same-headings(results) = {
  let first = results.first().result

  first.headings.len() > 0 and results.all(keyed => keyed.result.headings == first.headings and keyed.result.units == first.units)
}

#let keyed-body(entry, path) = {
  let results = entry.results

  if results.len() == 0 {
    rendered(path, none, "none")
    return secondary[no inputs]
  }

  if results.all(keyed => narrow(keyed.result)) {
    return rendered(path, none, "list") + keyed-list(results)
  }

  let computed = results.filter(keyed => not is-failure(keyed.result))
  let failed-keys = results.filter(keyed => is-failure(keyed.result))
  let kinds = computed.map(keyed => kind-of(keyed.result))

  if kinds.all(kind => kind == "distribution") {
    grouped-histogram(computed, path)
  } else if kinds.all(kind => kind == "histogram") and same-edges(computed) {
    grouped-histogram(computed, path)
  } else if kinds.all(kind => kind == "histogram") {
    stacked((secondary[the edges differ between the keys], keyed-blocks(computed, path)))
  } else if kinds.all(kind => kind == "counts") {
    grouped-counts(computed, path)
  } else if kinds.all(kind => kind == "table") and same-headings(computed) {
    rendered(path, "table", "table")
    stacked-table(computed)
  } else if kinds.all(kind => kind == "table") {
    stacked((secondary[the headings differ between the keys], keyed-blocks(computed, path)))
  } else {
    stacked((secondary[the results differ in kind between the keys], keyed-blocks(computed, path)))
  }

  failures(failed-keys)
}


#let breakable-cell(span, caption, drawn) = {
  table.cell(
    colspan: span,
    inset: (top: space.base, bottom: space.loose),
    layout(available => {
      let held = measure(caption, width: available.width).height
      let tall = measure(drawn, width: available.width).height > unbroken * page.height

      block(sticky: held < tallest-caption, caption)
      v(space.snug)
      block(breakable: tall, drawn)
    }),
  )
}

#let keyed-cell(entry, span, path) = {
  breakable-cell(span, caption(entry), keyed-body(entry, path + (entry.name,)))
}

#let wide-cell(entry, span, path) = {
  breakable-cell(span, caption(entry), body(entry.result, entry.title, path + (entry.name,)))
}

#let row-cells(entry, checked, path) = {
  let cells = (
    block(breakable: false, caption(entry)),
    block(breakable: false, { rendered(path + (entry.name,), kind-of(entry.result), "value"); result(entry.result) }),
  )

  if checked {
    cells.push(check(entry.result))
  }

  cells
}

#let listing(entries, checked, path) = {
  let columns = if checked { (1fr, width.value, width.check) } else { (1fr, width.value) }
  let span = columns.len()

  let cells = ()

  for entry in entries {
    if entry.kind == "keyed_analytic" {
      cells.push(keyed-cell(entry, span, path))
    } else if is-wide(entry) {
      cells.push(wide-cell(entry, span, path))
    } else {
      cells += row-cells(entry, checked, path)
    }
  }

  set text(number-width: "tabular")

  block(
    width: 100%,
    above: space.snug,
    below: space.loose,
    table(
      columns: columns,
      stroke: (x: none, top: none, bottom: lines.hairline),
      inset: (x: 0pt, y: space.base),
      align: (left + top, right + top, left + top).slice(0, span),
      ..cells,
    ),
  )
}


#let inputs-of(entries) = {
  stacked(entries.map(input => [
    #input.name: #counted(input.node_count, "node"), #counted(input.edge_count, "edge")
  ]))
}

#let with-inputs(items, entries) = {
  if entries.len() == 0 { items } else { items + (("Inputs", inputs-of(entries)),) }
}

#let failure-line(failure) = {
  if failure-details {
    [#failed #failure.exception_type: #failure.message]
  } else {
    failed
  }
}

#let derivation-line(derivation) = {
  let parts = ()

  if parameter-lines and derivation.parameters.len() > 0 {
    parts.push(pairs(derivation.parameters))
  }

  if derivation.summary.len() > 0 {
    parts.push(pairs(derivation.summary))
  }

  if derivation.failure != none {
    parts.push(failure-line(derivation.failure))
  }

  parts
}

#let facts(entry, parent-inputs) = {
  let items = ()

  if entry.inputs.len() > 0 and entry.inputs != parent-inputs {
    items = with-inputs(items, entry.inputs)
  }

  if entry.kind == "keyed_group" and entry.derivations.len() > 0 {
    items.push((
      "Derivations",
      stacked(entry.derivations.map(keyed => {
        let parts = derivation-line(keyed.derivation)

        if parts.len() == 0 { parts.push(secondary[completed]) }

        [#scalar(keyed.key): #parts.join([ ])]
      })),
    ))
  }

  if entry.kind == "group" and entry.derivation != none {
    let derivation = entry.derivation

    if parameter-lines and derivation.parameters.len() > 0 {
      items.push(("Parameters", pairs(derivation.parameters)))
    }

    if derivation.summary.len() > 0 {
      items.push(("Summary", pairs(derivation.summary)))
    }

    if derivation.failure != none {
      items.push(("Derivation", failure-line(derivation.failure)))
    }
  }

  if items.len() > 0 {
    block(width: 100%, above: 0pt, below: space.base, deflist(items))
  }
}

#let render(entries, depth, inputs, path) = {
  let analytics = entries.filter(entry => entry.kind in leaf-kinds)
  let groups = entries.filter(entry => entry.kind in section-kinds)
  let checked = analytics.any(entry => entry.kind == "analytic" and is-assessment(entry.result))

  if analytics.len() > 0 {
    listing(analytics, checked, path)
  }

  for (position, entry) in groups.enumerate() {
    if depth == 1 and (position > 0 or analytics.len() > 0) and section-breaks {
      pagebreak(weak: true)
    }

    heading(depth: depth, entry.title)

    if entry.description != none {
      block(width: 100%, above: 0pt, below: space.base, secondary(entry.description))
    }

    facts(entry, inputs)

    if entry.entries.len() == 0 {
      block(width: 100%, above: 0pt, below: space.base, secondary[no entries])
    }

    render(entry.entries, depth + 1, entry.inputs, path + (entry.name,))
  }
}


#let failure-of(value) = {
  if is-failure(value) { "failed" } else { "completed" }
}

#let timings(entries, path) = {
  let items = ()

  for entry in entries.filter(entry => entry.kind == "analytic") {
    let here = path + (entry.name,)

    items.push((here.map(scalar).join(" / "), failure-of(entry.result), seconds(entry.duration)))
  }

  for entry in entries.filter(entry => entry.kind == "keyed_analytic") {
    let here = path + (entry.name,)

    for keyed in entry.results {
      items.push((
        [#here.map(scalar).join(" / ") (#scalar(keyed.key))],
        failure-of(keyed.result),
        seconds(keyed.duration),
      ))
    }
  }

  for entry in entries.filter(entry => entry.kind in section-kinds) {
    let here = path + (entry.name,)

    if entry.kind == "group" and entry.derivation != none {
      let derivation = entry.derivation

      items.push((
        here.map(scalar).join(" / ") + " (derivation)",
        failure-of(derivation.failure),
        seconds(derivation.duration),
      ))
    }

    if entry.kind == "keyed_group" {
      for keyed in entry.derivations {
        items.push((
          [#here.map(scalar).join(" / ") (derivation, #scalar(keyed.key))],
          failure-of(keyed.derivation.failure),
          seconds(keyed.derivation.duration),
        ))
      }
    }

    items += timings(entry.entries, here)
  }

  items
}


#let wordmark(width) = {
  if logo == "" {
    text(weight: "bold", fill: palette.navy, company.name)
  } else {
    image(bytes(logo), format: "svg", width: width, alt: company.name)
  }
}

#let running-header = context {
  if counter(page).get().first() == 1 {
    return
  }

  grid(
    columns: (auto, 1fr),
    align: (left + horizon, right + horizon),
    wordmark(width.running-wordmark),
    secondary(report.name),
  )
  v(space.tight)
  line(length: 100%, stroke: lines.rule)
}

#let running-footer = {
  line(length: 100%, stroke: lines.rule)
  v(space.tight)
  grid(
    columns: (1fr, auto),
    align: (left, right),
    secondary[
      #company.name · #company.street · #company.city ·
      #company.web
    ],
    secondary(context [Page #counter(page).display("1 of 1", both: true)]),
  )
}

#let masthead = grid(
  columns: (1fr, auto),
  align: (left + bottom, right + bottom),
  wordmark(width.wordmark),
  secondary(
    if logo != "" [
      #text(fill: palette.ink, company.name) \
      #company.street, #company.city \
      #link("https://" + company.web)[#company.web] ·
      #link("mailto:" + company.mail)[#company.mail]
    ] else [
      #company.street, #company.city \
      #link("https://" + company.web)[#company.web] ·
      #link("mailto:" + company.mail)[#company.mail]
    ],
  ),
)


#set document(title: report.name, author: company.name, description: report.description)
#set page(
  paper: "a4",
  margin: (x: 2.2cm, top: 2.8cm, bottom: 2.6cm),
  numbering: "1",
  header: running-header,
  footer: running-footer,
)
#set text(font: fonts.text, size: size.body, fill: palette.ink)
#set strong(delta: 200)
#set par(leading: 0.55em)
#set heading(numbering: "1.1")
#show title: set text(size: size.title, weight: "bold", fill: palette.navy)
#show heading: set block(above: space.wide, below: space.base)
#show heading: set text(fill: palette.navy, weight: "bold")
#show heading.where(level: 1): set text(size: size.section)
#show heading.where(level: 2): set text(size: size.subsection)
#show heading.where(level: 3): set text(size: size.minor)
#show heading.where(level: 4): set text(size: size.body)
#show heading.where(level: 5): set text(size: size.body, style: "italic")
#show heading: it => {
  if it.level <= heading-steps.len() { return it }

  text(..heading-steps.last(), it)
}
#show regex("\\S{" + str(longest-word) + ",}"): it => {
  it.text.clusters().chunks(word-piece).map(piece => piece.join()).join(sym.zws)
}

#masthead
#v(space.wide)
#block(above: 0pt, below: space.loose, {
  text(fill: palette.muted, kind)
  v(space.hair)
  title()

  if report.description != none {
    v(space.tight)
    text(fill: palette.muted, report.description)
  }
})
#deflist(with-inputs(
  (
    ("Started", moment(report.started_at)),
    ("Duration", seconds(report.duration)),
    ("Rendered", "medrecords " + options.version),
  ),
  report.inputs,
))
#if report.entries.len() == 0 {
  block(width: 100%, above: space.base, below: 0pt, secondary[no entries])
}
#render(report.entries, 1, report.inputs, ())

#if run-details {
  let items = timings(report.entries, ())

  pagebreak(weak: true)
  heading(level: 1, numbering: none)[Run details]

  if items.len() == 0 {
    block(width: 100%, above: space.base, below: 0pt, secondary[no entries])
  } else {
    block(
      width: 100%,
      above: space.base,
      below: 0pt,
      sheet(
        (1fr, width.label, width.label),
        (left, left, right),
        ("Entry", "Outcome", "Duration"),
        items.flatten(),
      ),
    )
  }
}

#let report = json(bytes(sys.inputs.report))
#let logo = sys.inputs.logo
#let options = json(bytes(sys.inputs.options))

#let kind = options.kind
#let run-details = options.run_details
#let section-breaks = options.section_breaks

#let palette = (
  navy: rgb("#03045E"),
  tint: rgb("#F0F9FC"),
  ink: rgb("#0F172A"),
  muted: rgb("#64748B"),
  line: rgb("#E2E8F0"),
  alert: rgb("#B91C1C"),
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

#let long-table = 15

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

#let wide-kinds = ("table", "plot", "distribution")


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

#let seconds(duration) = {
  let sign = if duration < 0 { "−" } else { "" }
  let magnitude = calc.abs(duration)
  let scaled(value, unit) = sign + padded(value, 1) + " " + unit

  if magnitude < 0.0001 and magnitude != 0 {
    sign + "< 0.1 ms"
  } else if magnitude < 1 {
    scaled(magnitude * 1000, "ms")
  } else if magnitude < seconds-per.minute {
    scaled(magnitude, "s")
  } else if magnitude < seconds-per.hour {
    scaled(magnitude / seconds-per.minute, "min")
  } else if magnitude < seconds-per.day {
    scaled(magnitude / seconds-per.hour, "h")
  } else {
    scaled(magnitude / seconds-per.day, "d")
  }
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

#let numeric(value) = {
  type(value) in (int, float) or kind-of(value) in ("timedelta", "float")
}

#let scalar(value) = {
  if value == none {
    text(fill: palette.muted)[none]
  } else if type(value) == bool {
    if value { "true" } else { "false" }
  } else if type(value) == float {
    fixed(value)
  } else if kind-of(value) == "timedelta" {
    seconds(
      value.days * seconds-per.day
        + value.seconds
        + value.microseconds * seconds-per.microsecond,
    )
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

  if entry.parameters.len() > 0 {
    items.push(pairs(entry.parameters))
  }

  if is-failure(entry.result) {
    items.push(secondary[
      #entry.result.exception_type: #entry.result.message
    ])
  }

  block(stacked(items))
}

#let measurement(value) = {
  let items = (emphasized(scalar(value.value)),)

  if value.lower != none and value.upper != none {
    items.push(secondary[interval #scalar(value.lower) to #scalar(value.upper)])
  } else if value.lower != none {
    items.push(secondary[lower bound #scalar(value.lower)])
  } else if value.upper != none {
    items.push(secondary[upper bound #scalar(value.upper)])
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

#let result(value) = {
  if kind-of(value) == "measurement" {
    measurement(value)
  } else if is-assessment(value) {
    emphasized(scalar(value.value))
  } else if is-failure(value) {
    alert[error]
  } else {
    emphasized(scalar(value))
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

  let aligns = range(count).map(index => {
    let cells = value.rows.map(row => row.at(index)).filter(cell => cell != none)

    if cells.len() > 0 and numeric(cells.first()) { right } else { left }
  })
  let columns = range(count).map(index => {
    let lengths = value.rows.map(row => {
      let cell = row.at(index)

      if type(cell) == str { cell.clusters().len() } else { 0 }
    })

    if calc.max(value.headings.at(index).clusters().len(), ..lengths) > longest-cell {
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
      sheet(columns, aligns, value.headings, value.rows.flatten().map(scalar)),
    )),
  )
}

#let counted(number, noun) = str(number) + " " + noun + (if number == 1 { "" } else { "s" })

#let histogram(value) = {
  let bins = value.histogram
  let tallest = calc.max(..bins.map(bin => bin.count))
  let summary = value.summary
  let tracks = bins.len() * (1fr,)

  let mark(body) = text(size: size.tiny, fill: palette.muted, body)

  let bar(bin) = stack(
    dir: ttb,
    spacing: space.tight,
    align(center, mark(str(bin.count))),
    rect(width: 100%, height: chart.height * bin.count / tallest, fill: palette.navy),
  )

  let step = bins.first().upper - bins.first().lower
  let exponential = bins.any(bin => {
    let magnitude = calc.max(calc.abs(bin.lower), calc.abs(bin.upper))

    magnitude >= largest or (magnitude != 0 and magnitude < smallest)
  })
  let marked(number) = mark(short(number, step, exponential))
  let edge(index, bin) = {
    if index < bins.len() - 1 { return marked(bin.lower) }

    box(width: 100%)[#marked(bin.lower) #h(1fr) #marked(bin.upper)]
  }

  let spread = (
    summary.mean,
    summary.std,
    summary.minimum,
    summary.lower_quartile,
    summary.median,
    summary.upper_quartile,
    summary.maximum,
  )
  let figures = sheet(
    8 * (1fr,),
    8 * (right,),
    ("n", "mean", "std", "min", "q1", "median", "q3", "max"),
    (str(summary.count),) + spread.map(fixed),
  )

  if bins.len() == 1 {
    let wording = if summary.minimum == summary.maximum {
      [of #scalar(summary.minimum)]
    } else {
      [between #scalar(summary.minimum) and #scalar(summary.maximum)]
    }

    return block(width: 100%, breakable: false, {
      secondary[#counted(summary.count, "value") #wording]
      v(space.loose)
      figures
    })
  }

  block(width: 100%, breakable: false, {
    box(
      width: 100%,
      height: chart.height + size.tiny + space.snug,
      grid(columns: tracks, column-gutter: space.snug, align: bottom, ..bins.map(bar)),
    )
    line(length: 100%, stroke: lines.axis)
    v(space.hair)
    grid(columns: tracks, column-gutter: space.snug, ..bins.enumerate().map(((index, bin)) => edge(index, bin)))
    v(space.loose)
    figures
  })
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

#let body(value, title) = {
  if value.kind == "table" {
    tabular(value)
  } else if value.kind == "plot" {
    picture(value.svg, title)
  } else {
    histogram(value)
  }
}


#let wide-cell(entry, span) = {
  let together = entry.result.kind != "table" or entry.result.rows.len() <= long-table

  table.cell(
    colspan: span,
    inset: (top: space.base, bottom: space.loose),
    layout(available => {
      let held = measure(caption(entry), width: available.width).height

      block(sticky: held < tallest-caption, caption(entry))
      v(space.snug)
      block(breakable: not together, body(entry.result, entry.title))
    }),
  )
}

#let row-cells(entry, checked) = {
  let cells = (
    block(breakable: false, caption(entry)),
    block(breakable: false, result(entry.result)),
  )

  if checked {
    cells.push(check(entry.result))
  }

  cells
}

#let listing(entries, checked) = {
  let columns = if checked { (1fr, width.value, width.check) } else { (1fr, width.value) }
  let span = columns.len()

  let cells = ()

  for entry in entries {
    if is-wide(entry) {
      cells.push(wide-cell(entry, span))
    } else {
      cells += row-cells(entry, checked)
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

#let facts(entry, parent-inputs) = {
  let items = ()

  if entry.inputs.len() > 0 and entry.inputs != parent-inputs {
    items = with-inputs(items, entry.inputs)
  }

  if entry.derivation != none {
    let derivation = entry.derivation

    if derivation.parameters.len() > 0 {
      items.push(("Parameters", pairs(derivation.parameters)))
    }

    if derivation.summary.len() > 0 {
      items.push(("Summary", pairs(derivation.summary)))
    }

    if derivation.outcome != none {
      let outcome = derivation.outcome

      items.push((
        "Derivation",
        [#alert[error] #outcome.exception_type: #outcome.message],
      ))
    }
  }

  if items.len() > 0 {
    block(width: 100%, above: 0pt, below: space.base, deflist(items))
  }
}

#let render(entries, depth, inputs) = {
  let analytics = entries.filter(entry => entry.kind == "analytic")
  let groups = entries.filter(entry => entry.kind == "group")
  let checked = analytics.any(entry => is-assessment(entry.result))

  if analytics.len() > 0 {
    listing(analytics, checked)
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

    render(entry.entries, depth + 1, entry.inputs)
  }
}


#let outcome-of(value) = {
  if is-failure(value) { "failed" } else { "completed" }
}

#let timings(entries, path) = {
  let items = ()

  for entry in entries.filter(entry => entry.kind == "analytic") {
    let here = path + (entry.name,)

    items.push((here.join(" / "), outcome-of(entry.result), seconds(entry.duration)))
  }

  for entry in entries.filter(entry => entry.kind == "group") {
    let here = path + (entry.name,)

    if entry.derivation != none {
      let derivation = entry.derivation

      items.push((
        here.join(" / ") + " (derivation)",
        outcome-of(derivation.outcome),
        seconds(derivation.duration),
      ))
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
  (("Started", moment(report.started_at)), ("Duration", seconds(report.duration))),
  report.inputs,
))
#if report.entries.len() == 0 {
  block(width: 100%, above: space.base, below: 0pt, secondary[no entries])
}
#render(report.entries, 1, report.inputs)

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

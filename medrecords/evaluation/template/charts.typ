// The pictures: histograms, counts, scatters and plots, drawn with Lilaq.

#import "@preview/lilaq:0.6.0" as lq
#import "style.typ": *
#import "numbers.typ": *
#import "tables.typ": kept, numeric-cell, sheet

#let chart-style(body) = {
  show: lq.theme.skyline
  show: lq.set-spine(stroke: lines.spine)
  show: lq.set-tick(stroke: lines.spine, inset: 0pt, outset: chart.tick)
  show lq.selector(lq.tick-label): set text(fill: palette.muted, size: size.tiny)
  show lq.selector(lq.label): set text(fill: palette.ink, size: size.tiny)
  show: lq.set-grid(stroke: lines.grid)
  show: lq.cond-set(lq.grid.with(kind: "x"), stroke: none)
  show: lq.set-tick(pad: chart.tick-pad)
  show: lq.set-label(pad: chart.label-pad)
  show: lq.set-legend(stroke: none, fill: none, inset: 0pt, pad: 0pt)
  show lq.selector(lq.legend): set text(size: size.tiny)
  show math.equation: set text(font: fonts.text)

  body
}

#let rendered(path, kind, picture, scale: none) = [
  #metadata((path: path, kind: kind, picture: picture, scale: scale)) <rendering>
]

#let caption-text(body) = text(size: size.tiny, fill: palette.ink, body)

#let default-noun = "values"

#let noun-of(label) = if label == none { default-noun } else { label }

// The counted noun for one value: the plural without its final "s".
#let noun-for(number, noun) = if number == 1 and noun.ends-with("s") { noun.slice(0, -1) } else { noun }

// "2815 intervals", "1 interval".
#let amount(number, noun) = grouped(number) + " " + noun-for(number, noun)

// Panels when they are asked for or there are more keys than series colours, else one
// overlaid diagram.
#let arrangement-of(values, count) = {
  let declared = values.map(value => value.arrangement).filter(arrangement => arrangement != none)

  if count > palette.series.len() or declared.first(default: none) == "panels" { "panels" } else { "overlay" }
}

// Each key in its series colour when overlaid; every panel in the first.
#let coloured(series, arrangement) = series.enumerate().map(((index, one)) => {
  one + (colour: if arrangement == "overlay" { palette.series.at(index) } else { palette.series.first() })
})

// Tick labels in the template's number style, with the decimals of the tick distance
// where the tick locator states them.
#let number-ticks(ticks, tick-info: (:), ..rest) = {
  let places = tick-info.at("significant-digits", default: none)

  ticks.map(tick => if places == none { shortest(tick) } else { padded(tick, calc.max(0, places)) })
}

#let percent-ticks(ticks, tick-info: (:), ..rest) = {
  let places = calc.max(0, tick-info.at("significant-digits", default: 0) - 2)

  ticks.map(tick => padded(tick * 100, places) + "%")
}

// Never ticks between whole numbers when the values are integers.
#let value-axis(bins) = (
  subticks: none,
  format-ticks: number-ticks,
  tick-distance: if bins.whole-numbers { (min: 1) } else { auto },
)

#let share-axis = (subticks: none, format-ticks: percent-ticks)

// A legend of one row for up to three series, the entries of more in rows of three.
#let legend-columns(body, count) = {
  show lq.selector(lq.legend): set grid(columns: 2 * calc.min(count, chart.legend-row), column-gutter: space.tight)

  body
}

// The height of a horizontal axis under the data area: its tick, tick labels and
// caption with the paddings set on them.
#let axis-height(caption) = {
  let labels = measure(text(size: size.tiny, "0")).height
  let captioned = if caption == none { 0pt } else { chart.label-pad + measure(text(size: size.tiny, caption)).height }

  chart.tick + chart.tick-pad + labels + captioned
}

// A legend under the axis of the data area.
#let below-axis(caption) = (position: left + top, dy: 100% + axis-height(caption) + space.snug)

#let binned(value) = {
  let histogram = if value.kind == "distribution" { value.histogram } else { value }

  (
    edges: histogram.edges,
    counts: histogram.counts,
    below: histogram.below_count,
    above: histogram.above_count,
    scale: histogram.scale,
    whole-numbers: histogram.whole_numbers,
    statistics: value.statistics,
    value-label: value.value_label,
    count-label: value.count_label,
    arrangement: value.arrangement,
  )
}

#let histogram-series(key, value) = {
  let bins = binned(value)
  let total = bins.counts.sum(default: 0) + bins.below + bins.above

  (
    key: key,
    bins: bins,
    total: total,
    shares: bins.counts.map(count => if total == 0 { 0 } else { count / total }),
  )
}

// The bars of the first series, the step lines of the others, each at its true width.
#let histogram-marks(series, noun, filled: index => index == 0, labelled: true) = {
  let edges = series.first().bins.edges
  let widths = edges.windows(2).map(((lower, upper)) => upper - lower)

  series
    .enumerate()
    .map(((index, one)) => {
      let label = if labelled and one.key != none { [#scalar(one.key), #amount(one.total, noun)] }

      if filled(index) {
        lq.bar(edges.slice(0, -1), one.shares, width: widths, align: left, fill: one.colour, stroke: 0.4pt + white, label: label)
      } else {
        lq.plot(edges, one.shares + (one.shares.last(),), step: end, mark: none, stroke: chart.step + one.colour, label: label)
      }
    })
}

#let value-caption(label, scale) = {
  if scale != "logarithmic" { return label }
  if label == none { return "logarithmic scale" }

  label + ", logarithmic scale"
}

#let histogram-diagram(series, noun, width, height, ylim, filled: index => index == 0, labelled: true) = {
  let first = series.first().bins
  let captions = if labelled {
    (xlabel: value-caption(first.value-label, first.scale), ylabel: [share of #noun])
  } else {
    (:)
  }

  lq.diagram(
    width: width,
    height: height,
    margin: (x: 0%, top: 6%, bottom: 0%),
    xscale: if first.scale == "logarithmic" { "log" } else { "linear" },
    xlim: (first.edges.first(), first.edges.last()),
    ylim: ylim,
    xaxis: value-axis(first),
    yaxis: share-axis,
    legend: below-axis(captions.at("xlabel", default: none)),
    ..captions,
    ..histogram-marks(series, noun, filled: filled, labelled: labelled),
  )
}

// "Outside the axis: 1 synthetic interval below 0.2, 3 synthetic intervals above 5000."
// Integers below the first edge are at most the integer under it, those above the last
// at least the integer over it.
#let outside-line(series, noun) = {
  let first = series.first().bins
  let (lowest, highest) = (first.edges.first(), first.edges.last())
  let below = if first.whole-numbers { [at #grouped(calc.ceil(lowest) - 1) or less] } else { [below #shortest(lowest)] }
  let above = if first.whole-numbers { [at #grouped(calc.floor(highest) + 1) or more] } else { [above #shortest(highest)] }
  let part(one, count, side) = {
    let who = if one.key == none { "" } else { scalar(one.key) + " " }

    [#grouped(count) #who#noun-for(count, noun) #side]
  }
  let parts = series.filter(one => one.bins.below > 0).map(one => part(one, one.bins.below, below))

  parts += series.filter(one => one.bins.above > 0).map(one => part(one, one.bins.above, above))

  if parts.len() > 0 { block(above: space.snug, below: 0pt, secondary[Outside the axis: #parts.join(", ").]) }
}

#let statistics-headings = ("n", "mean", "sd", "min", "q1", "median", "q3", "max")

// One row per series that has values; "withheld" where a series has no statistics. The
// ranks of integers print exactly.
#let statistics-sheet(series) = {
  let counted = series.filter(one => one.total > 0)

  if counted.all(one => one.bins.statistics == none) { return }

  let keyed = counted.any(one => one.key != none)
  let ranked = if series.first().bins.whole-numbers { shortest } else { significant }
  let row(one) = {
    let lead = if keyed { (scalar(one.key),) } else { () }
    let statistics = one.bins.statistics

    if statistics == none {
      return lead + (numeric-cell(grouped(one.total)), table.cell(colspan: 7, align: right, secondary[withheld]))
    }

    let deviation = statistics.standard_deviation
    let ranks = (statistics.minimum, statistics.lower_quartile, statistics.median, statistics.upper_quartile, statistics.maximum)

    (
      lead
        + (
          numeric-cell(grouped(statistics.count)),
          numeric-cell(significant(statistics.mean)),
          if deviation == none { scalar(none) } else { numeric-cell(significant(deviation)) },
        )
        + ranks.map(number => numeric-cell(ranked(number)))
    )
  }
  let headings = (if keyed { ("",) } else { () }) + statistics-headings
  let aligns = (if keyed { (left,) } else { () }) + statistics-headings.map(heading => right)

  block(above: space.loose, below: 0pt, kept(sheet(headings.len() * (auto,), aligns, headings, counted.map(row).flatten())))
}

#let panel-columns(count, available) = {
  let fitting = calc.floor((available + chart.panel-gap) / (chart.panel + chart.panel-gap))

  calc.max(1, calc.min(count, fitting))
}

#let panel-title(one, noun) = stack(
  dir: ttb,
  spacing: space.hair,
  caption-text(scalar(one.key)),
  text(size: size.tiny, fill: palette.muted, amount(one.total, noun)),
)

// The picture of histograms sharing their edges, overlaid in one diagram or in panels
// on shared axes, with the values outside the axis named under it, kept on one page;
// the statistics sheet under it.
#let histogram-picture(series, path, kind) = layout(available => {
  let first = series.first().bins
  let noun = noun-of(first.count-label)
  let arrangement = arrangement-of(series.map(one => one.bins), series.len())
  let series = coloured(series, arrangement)
  let counted = series.filter(one => one.total > 0)

  if counted.len() == 0 { return rendered(path, kind, "none") + secondary[no values] }

  if arrangement == "panels" {
    let columns = panel-columns(series.len(), available.width)
    let tallest = calc.max(..counted.map(one => calc.max(..one.shares)))
    let panels = series.map(one => stack(
      dir: ttb,
      spacing: space.snug,
      panel-title(one, noun),
      histogram-diagram((one,), noun, 100%, chart.panel-height, (0, tallest), filled: index => true, labelled: false),
    ))

    rendered(path, kind, "panels", scale: first.scale)
    let caption = value-caption(first.value-label, first.scale)

    block(breakable: false, sticky: true, {
      block(above: 0pt, below: space.snug, caption-text[share of #noun])
      grid(columns: columns * (1fr,), column-gutter: chart.panel-gap, row-gutter: space.loose, align: bottom, ..panels)

      if caption != none { block(width: 100%, above: space.snug, below: 0pt, align(center, caption-text(caption))) }

      outside-line(series, noun)
    })
    statistics-sheet(series)
    return
  }

  let filled-key = counted.first().key
  let filled = index => counted.at(index).key == filled-key

  rendered(path, kind, "overlay", scale: first.scale)
  block(breakable: false, sticky: true, {
    if first.statistics == none and counted.first().key == none {
      block(above: 0pt, below: space.snug, caption-text(amount(counted.first().total, noun)))
    }

    legend-columns(histogram-diagram(counted, noun, 100%, chart.height, (0, auto), filled: filled), counted.len())
    outside-line(series, noun)
  })
  statistics-sheet(series)
})

#let agree(values) = {
  let first = values.first()

  values.all(value => value.edges == first.edges and value.scale == first.scale and value.arrangement == first.arrangement)
}

// A histogram or distribution, or those of several keys: overlaid or in panels when they
// share their edges, scale and arrangement, else each key on its own axis.
#let histogram-chart(results, path) = {
  let series = results.map(keyed => histogram-series(keyed.key, keyed.result))
  let kind = results.first().result.kind

  if agree(series.map(one => one.bins)) { return histogram-picture(series, path, kind) }

  rendered(path, kind, "apart")
  block(above: 0pt, below: space.snug, secondary[The keys differ in their bins, so each is drawn on its own axis.])
  stack(
    dir: ttb,
    spacing: space.loose,
    ..series.map(one => block(breakable: false, histogram-picture((one,), path + (one.key,), kind))),
  )
}

#let counts-series(key, value) = {
  let listed = value.counts.map(item => item.count).sum(default: 0)

  (key: key, value: value, total: value.total, remainder: value.total - listed)
}

#let count-of(value, category) = {
  let found = value.counts.find(item => item.value == category)

  if found == none { 0 } else { found.count }
}

// The rows of counts: the categories in the order the first series lists them, then
// those only later series list, then the remainder row.
#let count-rows(series) = {
  let categories = series.map(one => one.value.counts.map(item => item.value)).flatten().dedup()
  let first = series.first().value
  let remainder-name = if first.remainder_label == none { "other values" } else { first.remainder_label }
  let rows = categories.map(value => (
    label: category(value),
    counts: series.map(one => count-of(one.value, value)),
  ))

  if series.any(one => one.remainder > 0) {
    rows.push((label: text(fill: palette.muted)[#remainder-name], counts: series.map(one => one.remainder)))
  }

  rows
}

// The rows of counts in pieces no taller than the tallest chart, so a long list breaks
// across pages.
#let chunks(rows, row-height) = {
  let length = calc.max(1, calc.floor(chart.tallest / row-height))

  range(0, rows.len(), step: length).map(start => rows.slice(start, calc.min(start + length, rows.len())))
}

// The bars of a piece of the rows, the share at the end of every bar, in a data area of
// the given width; the category labels and their caption on the leftmost plot only.
#let counts-plot(rows, series, columns, tallest, noun, plot-width, label-width, caption, labelled, legend) = {
  show: lq.cond-set(lq.grid.with(kind: "x"), stroke: lines.grid)
  show: lq.cond-set(lq.grid.with(kind: "y"), stroke: none)

  let row-height = series.len() * chart.bar-slot + chart.category-gap
  let thickness = chart.bar / row-height
  let offset(index) = ((series.len() - 1) / 2 - index) * chart.bar-slot / row-height
  let positions = range(rows.len()).rev()
  let label-cell(row) = if labelled { block(width: label-width, align(right, row.label)) }
  let marks = ()

  for (index, one) in series.enumerate() {
    let column = columns.at(index)
    let values = rows.map(row => if one.total == 0 { 0 } else { row.counts.at(column) / one.total })
    let label = if legend and series.len() > 1 { [#scalar(one.key), #amount(one.total, noun)] }

    marks.push(lq.hbar(values, positions, offset: offset(index), width: thickness, fill: one.colour, label: label))

    if one.total > 0 {
      for (position, value) in positions.zip(values) {
        marks.push(lq.place(value, position + offset(index), pad(left: space.hair, text(
          size: size.tiny,
          fill: palette.muted,
          number-width: "tabular",
          share(value),
        )), align: left + horizon))
      }
    }
  }

  legend-columns(
    lq.diagram(
      width: plot-width,
      height: rows.len() * row-height,
      margin: 0%,
      xlim: (0, tallest),
      ylim: (-0.5, rows.len() - 0.5),
      xaxis: share-axis,
      yaxis: (ticks: positions.zip(rows).map(((position, row)) => (position, label-cell(row))), subticks: none),
      xlabel: [share of #noun],
      ylabel: if labelled { caption },
      legend: below-axis([share of #noun]),
      ..marks,
    ),
    series.len(),
  )
}

// Counts, or those of several keys: horizontal bars, a row per category and the
// remainder row, the share at the end of every bar; keys overlaid in one plot or each in
// a panel, every plot of one width so the scales match. A long list is drawn in pieces
// that break across pages, the legend kept with the first.
#let counts-picture(series, path) = layout(available => {
  let first = series.first().value
  let noun = noun-of(first.count_label)
  let rows = count-rows(series)
  let arrangement = arrangement-of(series.map(one => one.value), series.len())
  let series = coloured(series, arrangement)

  if series.all(one => one.total == 0) { return rendered(path, "counts", "none") + secondary[no values] }

  let largest = calc.max(..series.enumerate().map(((index, one)) => if one.total == 0 { 0 } else {
    calc.max(..rows.map(row => row.counts.at(index) / one.total))
  }))
  let tallest = if largest > 0 { lq.locate-ticks-linear(0, largest).ticks.last() } else { 1 }
  let tallest = if tallest < largest { tallest + lq.locate-ticks-linear(0, largest).tick-distance } else { tallest }
  let longest = calc.max(..rows.map(row => measure(text(size: size.tiny, row.label)).width))
  let label-width = calc.min(longest, available.width * chart.categories)
  let caption-width = if first.value_label == none { 0pt } else {
    chart.label-pad + measure(text(size: size.tiny, first.value_label)).height
  }
  let left = label-width + chart.tick + chart.tick-pad + caption-width
  let room = space.hair + measure(text(size: size.tiny, number-width: "tabular", share(1))).width
  let panels = arrangement == "panels"
  let groups = if panels { series.enumerate().map(((index, one)) => ((one,), (index,))) } else {
    ((series, range(series.len())),)
  }
  let row-height = (if panels { 1 } else { series.len() }) * chart.bar-slot + chart.category-gap
  let columns = if panels { panel-columns(series.len(), available.width) } else { 1 }
  let plot-width = (available.width - left - columns * (room + chart.panel-gap) + chart.panel-gap) / columns
  let pieces = chunks(rows, row-height)

  rendered(path, "counts", if panels { "panels" } else { "overlay" })

  for (position, piece) in pieces.enumerate() {
    let plots = groups
      .enumerate()
      .map(((index, (members, columns-of))) => {
        let leftmost = calc.rem(index, columns) == 0
        let plot = counts-plot(piece, members, columns-of, tallest, noun, plot-width, label-width, first.value_label, leftmost, position == 0)

        if panels and position == 0 { stack(dir: ttb, spacing: space.snug, panel-title(members.first(), noun), plot) } else { plot }
      })

    block(breakable: false, above: 0pt, below: space.snug, {
      if position == 0 and series.len() == 1 {
        block(above: 0pt, below: space.snug, caption-text(amount(series.first().total, noun)))
      }

      grid(columns: columns * (auto,), column-gutter: chart.panel-gap, row-gutter: space.loose, align: bottom, ..plots)
    })
  }
})

#let counts-chart(results, path) = {
  let series = results.map(keyed => counts-series(keyed.key, keyed.result))
  let arrangements = series.map(one => one.value.arrangement).dedup()

  if arrangements.len() <= 1 { return counts-picture(series, path) }

  rendered(path, "counts", "apart")
  block(above: 0pt, below: space.snug, secondary[The keys ask for different arrangements, so each is drawn apart.])
  stack(dir: ttb, spacing: space.loose, ..series.map(one => block(breakable: false, counts-picture((one,), path + (one.key,)))))
}

#let decade(value) = calc.pow(10.0, calc.floor(calc.log(value)))

// Tick labels of a symmetric logarithmic axis: zero and the decades, none on the ticks
// inside the linear stretch below the threshold.
#let symlog-ticks(threshold) = (ticks, ..rest) => ticks.map(tick => {
  if tick == 0 or calc.abs(tick) >= threshold { shortest(tick) }
})

// A scatter axis: linear with a twentieth of the span around the values; logarithmic over
// whole decades; symmetric logarithmic, linear below the decade of the smallest positive
// value, when a value at or below zero is drawn on a logarithmic axis.
#let scatter-axis(values, scale) = {
  let (lowest, highest) = (calc.min(..values), calc.max(..values))

  if scale != "logarithmic" {
    let margin = if highest > lowest { (highest - lowest) / 20 } else { calc.max(1, calc.abs(highest)) / 20 }

    return (scale: "linear", lim: (lowest - margin, highest + margin), ticks: number-ticks)
  }

  let positive = values.filter(value => value > 0)
  let smallest = if positive.len() == 0 { 1 } else { calc.min(..positive) }
  let largest = if positive.len() == 0 { 1 } else { calc.max(..positive) }
  let top = calc.max(decade(largest) * 10, decade(smallest) * 10)

  if lowest > 0 { return (scale: "log", lim: (decade(smallest), top), ticks: number-ticks) }

  let threshold = decade(smallest)
  let bottom = if lowest == 0 { 0 } else { -decade(-lowest) * 10 }

  (scale: lq.scale.symlog(threshold: threshold), lim: (bottom, top), ticks: symlog-ticks(threshold))
}

#let scatter-chart(value, path) = {
  if value.points.len() == 0 { return rendered(path, "scatter", "none") + secondary[no values] }

  let x-axis = scatter-axis(value.points.map(point => point.first()), value.x_scale)
  let y-axis = scatter-axis(value.points.map(point => point.last()), value.y_scale)
  let numbered = value.labels.enumerate().map(((position, item)) => (
    number: position + 1,
    point: value.points.at(item.index),
    label: item.label,
  ))
  let diagonal-start = calc.max(x-axis.lim.first(), y-axis.lim.first())
  let diagonal-end = calc.min(x-axis.lim.last(), y-axis.lim.last())
  let diagonal = if value.diagonal and diagonal-start < diagonal-end {
    (lq.line((diagonal-start, diagonal-start), (diagonal-end, diagonal-end), stroke: lines.spine, z-index: 1),)
  } else { () }

  block(breakable: false, context {
    rendered(path, "scatter", "scatter")
    lq.diagram(
      width: chart.scatter,
      height: chart.scatter,
      margin: 0%,
      xscale: x-axis.scale,
      yscale: y-axis.scale,
      xlim: x-axis.lim,
      ylim: y-axis.lim,
      xaxis: (subticks: none, format-ticks: x-axis.ticks),
      yaxis: (subticks: none, format-ticks: y-axis.ticks),
      xlabel: value.x_label,
      ylabel: value.y_label,
      legend: below-axis(value.x_label),
      ..diagonal,
      lq.scatter(
        value.points.map(point => point.first()),
        value.points.map(point => point.last()),
        color: palette.series.first(),
        size: chart.point,
        stroke: 0.5pt + white,
      ),
      ..numbered.map(one => lq.scatter(
        (one.point.first(),),
        (one.point.last(),),
        color: palette.navy,
        size: chart.point,
        stroke: 0.5pt + white,
        z-index: 3,
        label: [#strong(str(one.number)) #one.label],
      )),
      ..numbered.map(one => lq.place(
        one.point.first(),
        one.point.last(),
        pad(left: chart.point / 2 + space.hair, text(size: size.tiny, weight: "semibold", fill: palette.navy, str(one.number))),
        align: left + horizon,
      )),
    )
  })
}

#let picture(svg, description) = {
  let drawing = image(bytes(svg), format: "svg")

  layout(area => {
    let natural = measure(drawing)
    let ratio = calc.min(1.0, area.width / natural.width, chart.tallest / natural.height)

    image(bytes(svg), format: "svg", width: natural.width * ratio, alt: description)
  })
}

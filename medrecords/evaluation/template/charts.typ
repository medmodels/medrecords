// The pictures: histograms, counts, scatters and plots, drawn with Lilaq.

#import "@preview/lilaq:0.6.0" as lq
#import "style.typ": *
#import "numbers.typ": *
#import "tables.typ": fitted, numeric-cell, sheet

#let chart-style(body) = {
  show: lq.theme.skyline
  show: lq.set-spine(stroke: lines.spine)
  show: lq.set-tick(stroke: lines.spine, inset: 0pt, outset: chart.tick)
  show lq.selector(lq.tick-label): set text(fill: palette.muted, size: size.tiny)
  show lq.selector(lq.label): set text(fill: palette.ink, size: size.tiny)
  show: lq.set-grid(stroke: lines.grid)
  show: lq.cond-set(lq.grid.with(kind: "x"), stroke: none)
  show: lq.set-legend(stroke: none, fill: none, position: left + bottom, dy: -100%, pad: 0pt)
  show lq.selector(lq.legend): set text(size: size.tiny)
  show math.equation: set text(font: fonts.text)

  body
}

#let rendered(path, kind, picture, scale: none) = [
  #metadata((path: path, kind: kind, picture: picture, scale: scale)) <rendering>
]

#let caption-text(body) = text(size: size.tiny, fill: palette.ink, body)

#let series-colour(index) = palette.series.at(calc.rem(index, palette.series.len()))

#let default-noun = "values"

#let noun-of(label) = if label == none { default-noun } else { label }

// The counted noun for one value: the plural without its final "s".
#let noun-for(number, noun) = if number == 1 and noun.ends-with("s") { noun.slice(0, -1) } else { noun }

// "2815 intervals", "1 interval".
#let amount(number, noun) = grouped(number) + " " + noun-for(number, noun)

#let arrangement-of(values, count) = {
  let declared = values.map(value => value.arrangement).filter(arrangement => arrangement != none)

  if declared.len() > 0 { declared.first() } else if count <= overlaid-keys { "overlay" } else { "panels" }
}

// Tick labels in the template's number style; "0" at the tick a logarithmic scatter
// axis draws its values at or below zero on.
#let number-ticks(zero: none) = (ticks, ..rest) => ticks.map(tick => {
  if zero != none and calc.abs(tick - zero) <= even-tolerance * zero { "0" } else { exact(tick) }
})

// Tick labels as percent, one decimal more for every tenfold finer step below one percent.
#let percent-ticks(ticks, ..rest) = {
  let step = if ticks.len() > 1 { calc.abs(ticks.at(1) - ticks.at(0)) } else { 1 }
  let places = if step <= 0 { 0 } else { calc.max(0, calc.ceil(-calc.log(step * 100) - 1e-9)) }

  ticks.map(tick => padded(tick * 100, places) + "%")
}

// Whether the edges lie halfway between whole numbers, so the bins hold whole numbers.
#let whole-numbers(edges) = edges.all(edge => calc.abs(calc.fract(calc.abs(edge)) - 0.5) <= even-tolerance)

// A value axis on Lilaq's tick locators: never ticks between whole numbers when the bins
// hold whole numbers, and fewer ticks the longer the widest label.
#let value-axis(edges, scale) = {
  let widest = calc.max(..(edges.first(), edges.last()).map(edge => exact(edge).clusters().len()))
  let density = calc.min(100%, 100% * chart.short-label / widest)

  (
    subticks: none,
    format-ticks: number-ticks(),
    exponent: if scale == "logarithmic" { none } else { auto },
    tick-distance: if whole-numbers(edges) { (min: 1) } else { auto },
    tick-args: (density: density),
  )
}

#let share-axis = (subticks: none, format-ticks: percent-ticks)

// A legend of one row for up to three series, the entries of more in rows of three.
#let legend-columns(body, count) = {
  show lq.selector(lq.legend): set grid(columns: 2 * calc.min(count, chart.legend-row), column-gutter: space.tight)

  body
}

#let binned(value) = {
  let histogram = if value.kind == "distribution" { value.histogram } else { value }

  (
    edges: histogram.edges,
    counts: histogram.counts,
    below: histogram.below_count,
    above: histogram.above_count,
    scale: histogram.scale,
    statistics: value.statistics,
    value-label: value.value_label,
    count-label: value.count_label,
    arrangement: value.arrangement,
  )
}

#let histogram-series(index, key, value) = {
  let bins = binned(value)
  let total = bins.counts.sum(default: 0) + bins.below + bins.above

  (
    key: key,
    colour: series-colour(index),
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
    xaxis: value-axis(first.edges, first.scale),
    yaxis: share-axis,
    ..captions,
    ..histogram-marks(series, noun, filled: filled, labelled: labelled),
  )
}

// "Outside the axis: 1 synthetic interval below 0.2, 3 synthetic intervals above 5000."
#let outside-line(series, noun) = {
  let edges = series.first().bins.edges
  let whole = whole-numbers(edges)
  let below = if whole { [at #grouped(int(calc.round(edges.first() - 0.5))) or less] } else { [below #exact(edges.first())] }
  let above = if whole { [at #grouped(int(calc.round(edges.last() + 0.5))) or more] } else { [above #exact(edges.last())] }
  let part(one, count, side) = {
    let who = if one.key == none { "" } else { scalar(one.key) + " " }

    [#grouped(count) #who#noun-for(count, noun) #side]
  }
  let parts = series.filter(one => one.bins.below > 0).map(one => part(one, one.bins.below, below))

  parts += series.filter(one => one.bins.above > 0).map(one => part(one, one.bins.above, above))

  if parts.len() > 0 { block(above: space.snug, below: 0pt, secondary[Outside the axis: #parts.join(", ").]) }
}

#let statistics-headings = ("n", "mean", "sd", "min", "q1", "median", "q3", "max")

#let statistics-numbers(statistics) = (
  statistics.mean,
  statistics.standard_deviation,
  statistics.minimum,
  statistics.lower_quartile,
  statistics.median,
  statistics.upper_quartile,
  statistics.maximum,
)

// One row per series that has values; "withheld" where a series has no statistics.
#let statistics-sheet(series) = {
  let counted = series.filter(one => one.total > 0)

  if counted.all(one => one.bins.statistics == none) { return }

  let keyed = counted.any(one => one.key != none)
  let whole = whole-numbers(series.first().bins.edges) and counted.all(one => {
    let statistics = one.bins.statistics

    statistics == none or (calc.fract(statistics.minimum) == 0 and calc.fract(statistics.maximum) == 0)
  })
  let row(one) = {
    let lead = if keyed { (scalar(one.key),) } else { () }
    let statistics = one.bins.statistics

    if statistics == none {
      return lead + (numeric-cell(grouped(one.total)), table.cell(colspan: 7, align: right, secondary[withheld]))
    }

    let (mean, deviation, ..ranks) = statistics-numbers(statistics)
    let ranked = if whole { exact } else { significant }

    (
      lead
        + (numeric-cell(grouped(statistics.count)), numeric-cell(significant(mean)), numeric-cell(significant(deviation)))
        + ranks.map(number => numeric-cell(ranked(number)))
    )
  }
  let headings = (if keyed { ("",) } else { () }) + statistics-headings
  let aligns = (if keyed { (left,) } else { () }) + statistics-headings.map(heading => right)
  let drawn = fitted(text-size => text(
    size: text-size,
    sheet(headings.len() * (auto,), aligns, headings, counted.map(row).flatten()),
  ))

  layout(available => block(
    above: space.loose,
    below: 0pt,
    breakable: measure(drawn, width: available.width).height > available.height,
    drawn,
  ))
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
  let counted = series.filter(one => one.total > 0)
  let arrangement = arrangement-of(series.map(one => one.bins), series.len())

  if counted.len() == 0 { return rendered(path, kind, "none") + secondary[no values] }

  if arrangement == "panels" and series.len() > 1 {
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
  let series = results.enumerate().map(((index, keyed)) => histogram-series(index, keyed.key, keyed.result))
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

#let counts-series(index, key, value) = {
  let listed = value.counts.map(item => item.count).sum(default: 0)

  (key: key, colour: series-colour(index), value: value, total: value.total, remainder: value.total - listed)
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

#let counts-plot(rows, series, columns, tallest, noun, label-width, labelled, legend) = {
  let row-height = series.len() * chart.bar-slot + chart.category-gap
  let thickness = chart.bar / row-height
  let offset(index) = ((series.len() - 1) / 2 - index) * chart.bar-slot / row-height
  let positions = range(rows.len()).rev()
  let label-cell(row) = block(width: label-width, align(right, row.label))
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

  lq.diagram(
    width: 100%,
    height: rows.len() * row-height,
    margin: 0%,
    xlim: (0, tallest),
    ylim: (-0.5, rows.len() - 0.5),
    xaxis: share-axis,
    yaxis: (ticks: positions.zip(rows).map(((position, row)) => (position, if labelled { label-cell(row) } else { "" })), subticks: none),
    xlabel: [share of #noun],
    ..marks,
  )
}

// Counts, or those of several keys: horizontal bars, a row per category and the
// remainder row, the share at the end of every bar. A long list is drawn in pieces
// that break across pages, the legend kept with the first and the caption with the last.
#let counts-picture(series, path) = layout(available => {
  let first = series.first().value
  let noun = noun-of(first.count_label)
  let rows = count-rows(series)
  let arrangement = arrangement-of(series.map(one => one.value), series.len())

  if series.all(one => one.total == 0) { return rendered(path, "counts", "none") + secondary[no values] }

  let tallest = calc.max(..series.enumerate().map(((index, one)) => if one.total == 0 { 0 } else {
    calc.max(..rows.map(row => row.counts.at(index) / one.total))
  }))
  let longest = calc.max(..rows.map(row => measure(text(size: size.tiny, row.label)).width))
  let label-width = calc.min(longest, available.width * chart.categories)
  let room = measure(text(size: size.tiny, number-width: "tabular", "100.0%")).width + space.tight
  let panels = arrangement == "panels" and series.len() > 1
  let groups = if panels { series.enumerate().map(((index, one)) => ((one,), (index,))) } else {
    ((series, range(series.len())),)
  }
  let row-height = (if panels { 1 } else { series.len() }) * chart.bar-slot + chart.category-gap
  let columns = if panels { panel-columns(series.len(), available.width) } else { 1 }
  let pieces = chunks(rows, row-height)

  rendered(path, "counts", if panels { "panels" } else { "overlay" })

  for (position, piece) in pieces.enumerate() {
    let plots = groups
      .enumerate()
      .map(((index, (members, columns-of))) => {
        let leftmost = calc.rem(index, columns) == 0
        let plot = pad(right: room, legend-columns(
          counts-plot(piece, members, columns-of, tallest, noun, label-width, leftmost, position == 0),
          members.len(),
        ))

        if panels and position == 0 { stack(dir: ttb, spacing: space.snug, panel-title(members.first(), noun), plot) } else { plot }
      })

    block(breakable: false, above: 0pt, below: space.snug, {
      if position == 0 and series.len() == 1 {
        block(above: 0pt, below: space.snug, caption-text(amount(series.first().total, noun)))
      }

      grid(columns: columns * (1fr,), column-gutter: chart.panel-gap, row-gutter: space.loose, align: bottom, ..plots)
    })
  }
})

#let counts-chart(results, path) = {
  let series = results.enumerate().map(((index, keyed)) => counts-series(index, keyed.key, keyed.result))
  let arrangements = series.map(one => one.value.arrangement).dedup()

  if arrangements.len() <= 1 { return counts-picture(series, path) }

  rendered(path, "counts", "apart")
  block(above: 0pt, below: space.snug, secondary[The keys ask for different arrangements, so each is drawn apart.])
  stack(dir: ttb, spacing: space.loose, ..series.map(one => block(breakable: false, counts-picture((one,), path + (one.key,)))))
}

// The limits of a scatter axis: on a logarithmic axis whole decades, starting a little
// below the decade under the smallest positive value when values at or below zero are
// drawn there, at the zero tick; else the values with a twentieth of their span around them.
#let scatter-limits(values, scale) = {
  if scale != "logarithmic" {
    let (lower, upper) = (calc.min(..values), calc.max(..values))
    let margin = if upper > lower { (upper - lower) / 20 } else { calc.max(1, calc.abs(upper)) / 20 }

    return (lim: (lower - margin, upper + margin), zero: none)
  }

  let positive = values.filter(value => value > 0)
  let smallest = if positive.len() == 0 { 1 } else { calc.min(..positive) }
  let largest = if positive.len() == 0 { 1 } else { calc.max(..positive) }
  let zeros = positive.len() < values.len()
  let start = calc.floor(calc.log(smallest)) - (if zeros { 1 } else { 0 })
  let stop = calc.max(calc.ceil(calc.log(largest)), start + 1)
  let zero = if zeros { calc.pow(10.0, start) }

  (lim: (if zeros { zero / chart.zero-margin } else { calc.pow(10.0, start) }, calc.pow(10.0, stop)), zero: zero)
}

// Where on the plot a value lies, in points from the axis start, for placing labels.
#let scatter-position(value, axis, scale, length) = {
  let (lower, upper) = axis.lim

  if scale == "logarithmic" {
    length * (calc.log(value) - calc.log(lower)) / (calc.log(upper) - calc.log(lower))
  } else {
    length * (value - lower) / (upper - lower)
  }
}

// The labels of a scatter placed left of their points, else right, above or below,
// wherever they stay inside the plot and meet no label placed before; the rest are
// listed under the chart.
#let scatter-labels(placed, size-of, plot-size) = {
  let boxes = ()
  let kept = ()
  let left-out = ()
  let gap = space.hair + chart.point / 2

  for point in placed {
    let (label-width, label-height) = size-of(point.label)
    let options = (
      (dx: -gap - label-width, dy: -label-height / 2, align: right + horizon),
      (dx: gap, dy: -label-height / 2, align: left + horizon),
      (dx: -label-width / 2, dy: -gap - label-height, align: center + bottom),
      (dx: -label-width / 2, dy: gap, align: center + top),
    )
    let chosen = options.find(option => {
      let left = point.x + option.dx
      let top = point.y + option.dy
      let inside = left >= 0pt and top >= 0pt and left + label-width <= plot-size and top + label-height <= plot-size

      inside and boxes.all(other => (
        left + label-width + chart.label-gap <= other.left
          or left >= other.left + other.width + chart.label-gap
          or top + label-height + chart.label-gap <= other.top
          or top >= other.top + other.height + chart.label-gap
      ))
    })

    if chosen == none {
      left-out.push(point.label)
    } else {
      boxes.push((left: point.x + chosen.dx, top: point.y + chosen.dy, width: label-width, height: label-height))
      kept.push((point: point, align: chosen.align))
    }
  }

  (kept: kept, left-out: left-out)
}

#let scatter-axis(axis, scale) = (
  subticks: none,
  format-ticks: number-ticks(zero: axis.zero),
  exponent: if scale == "logarithmic" { none } else { auto },
)

#let scatter-chart(value, path) = {
  if value.points.len() == 0 { return rendered(path, "scatter", "none") + secondary[no values] }

  let logarithmic(scale) = scale == "logarithmic"
  let x-axis = scatter-limits(value.points.map(point => point.first()), value.x_scale)
  let y-axis = scatter-limits(value.points.map(point => point.last()), value.y_scale)
  let at-zero(value, axis) = if axis.zero != none and value <= 0 { axis.zero } else { value }
  let drawn = value.points.map(((x, y)) => (at-zero(x, x-axis), at-zero(y, y-axis)))
  let placed = value.labels.map(item => {
    let (x, y) = drawn.at(item.index)

    (
      x: scatter-position(x, x-axis, value.x_scale, chart.scatter),
      y: chart.scatter - scatter-position(y, y-axis, value.y_scale, chart.scatter),
      data: (x, y),
      label: item.label,
    )
  })
  let measured = label => {
    let box-size = measure(text(size: size.tiny, label))

    (box-size.width, box-size.height)
  }
  let lower(axis) = if axis.zero == none { axis.lim.first() } else { axis.zero }
  let diagonal-start = calc.max(lower(x-axis), lower(y-axis))
  let diagonal-end = calc.min(x-axis.lim.last(), y-axis.lim.last())
  let diagonal = if value.diagonal and diagonal-start < diagonal-end {
    (lq.line((diagonal-start, diagonal-start), (diagonal-end, diagonal-end), stroke: lines.spine, z-index: 1),)
  } else { () }

  context block(breakable: false, {
    let (kept, left-out) = scatter-labels(placed, measured, chart.scatter)

    rendered(path, "scatter", "scatter")
    lq.diagram(
      width: chart.scatter,
      height: chart.scatter,
      margin: 0%,
      xscale: if logarithmic(value.x_scale) { "log" } else { "linear" },
      yscale: if logarithmic(value.y_scale) { "log" } else { "linear" },
      xlim: x-axis.lim,
      ylim: y-axis.lim,
      xaxis: scatter-axis(x-axis, value.x_scale),
      yaxis: scatter-axis(y-axis, value.y_scale),
      xlabel: value.x_label,
      ylabel: value.y_label,
      ..diagonal,
      lq.scatter(
        drawn.map(point => point.first()),
        drawn.map(point => point.last()),
        color: palette.series.first(),
        size: chart.point,
        stroke: 0.5pt + white,
      ),
      ..kept.map(found => lq.place(
        found.point.data.first(),
        found.point.data.last(),
        pad(space.hair + chart.point / 2, text(size: size.tiny, fill: palette.ink, found.point.label)),
        align: found.align,
      )),
    )

    if left-out.len() > 0 {
      block(above: space.snug, below: 0pt, secondary[Not labelled for lack of room: #left-out.join(", ").])
    }
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

// The inputs of the document and the constants every module sets it with; no logic.

#let report = json(bytes(sys.inputs.report))
#let logo = sys.inputs.logo
#let options = json(bytes(sys.inputs.options))
#let company = options.company

#let palette = (
  navy: rgb("#03045E"),
  tint: rgb("#F0F9FC"),
  ink: rgb("#0F172A"),
  muted: rgb("#64748B"),
  line: rgb("#E2E8F0"),
  axis: rgb("#94A3B8"),
  alert: rgb("#B91C1C"),
  series: (rgb("#0077B6"), rgb("#03045E"), rgb("#00B4D8")),
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
  wordmark: 6cm,
  running-wordmark: 2.4cm,
)

#let lines = (
  hairline: 0.5pt + palette.line,
  rule: 0.5pt + palette.ink,
  spine: 0.6pt + palette.axis,
  grid: 0.5pt + palette.line,
)

#let fonts = (
  text: "Inter",
)

#let cell = (
  across: 0.8em,
  down: 0.6em,
)

// The measures of the charts: plot heights, ticks and the paddings of their labels and
// of the axis captions, step lines, panels, bars of counts, the widest share of the width
// the category labels take, scatter points and plots.
#let chart = (
  height: 140pt,
  tallest: 420pt,
  tick: 3pt,
  tick-pad: 4pt,
  label-pad: 6pt,
  step: 1.4pt,
  panel: 80pt,
  panel-height: 64pt,
  panel-gap: 9pt,
  bar: 8pt,
  bar-slot: 10pt,
  category-gap: 6pt,
  categories: 40%,
  point: 6pt,
  scatter: 7cm,
  legend-row: 3,
)

#let numbered-levels = 3

#let decimals = 3

#let significant-digits = 3

// Floats from this magnitude on print as a power of ten; other floats below the
// smallest print as "< 10⁻¹²".
#let largest = 1e12

#let tiniest = 1e-12

// Floats below this magnitude keep three significant digits instead of three decimals.
#let smallest = 0.001

// Integers group their digits from this many digits on.
#let grouped-from = 5

#let seconds-per = (
  microsecond: 0.000001,
  minute: 60,
  hour: 3600,
  day: 86400,
)

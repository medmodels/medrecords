// Cover, contents and the running header and footer.

#import "style.typ": *
#import "numbers.typ": day-of, detail, secondary
#import "tables.typ": deflist

#let kind = options.kind

#let has-cover = options.cover

#let wordmark(wordmark-width) = {
  if logo == "" {
    if company != none { text(weight: "bold", fill: palette.navy, company.name) }
  } else {
    image(bytes(logo), format: "svg", width: wordmark-width, alt: if company != none { company.name })
  }
}

#let masthead = grid(
  columns: (1fr, auto),
  align: (left + bottom, right + bottom),
  wordmark(width.wordmark),
  secondary(if company == none [] else [
    #if logo != "" [#text(fill: palette.ink, company.name) \ ]
    #company.street, #company.city \
    #link("https://" + company.web)[#company.web] ·
    #link("mailto:" + company.mail)[#company.mail]
  ]),
)

#let identity = {
  text(fill: palette.muted, kind)
  v(space.hair)
  title()

  if report.description != none {
    v(space.tight)
    text(fill: palette.muted, report.description)
  }
}

#let parameters = report.parameters.pairs().map(((name, value)) => (name, detail(value)))

#let run-facts = (("Date", day-of(report.started_at)), ("Software", "medrecords " + options.version))

// The cover: its own page without header, footer or number, holding the masthead, the
// kind, the title, the description, the report's parameters, the date and the software.
#let cover-page() = page(header: none, footer: none, numbering: none, {
  masthead
  v(3 * space.wide)
  block(above: 0pt, below: space.wide, identity)

  if parameters.len() > 0 { deflist(parameters) }

  v(1fr)
  deflist(run-facts)
})

// The same block opening the first page when there is no cover page.
#let cover-block() = {
  masthead
  v(space.wide)
  block(above: 0pt, below: space.loose, identity)
  deflist(parameters + run-facts)
}

#let contents-page() = {
  pagebreak(weak: true)
  [#heading(level: 1, numbering: none, outlined: false, bookmarked: false)[Contents] <contents>]

  show outline.entry: it => link(it.element.location(), {
    show link: inner => inner.body
    it.indented(it.prefix(), it.inner())
  })

  outline(title: none, depth: numbered-levels, indent: auto)
  pagebreak(weak: true)
}

// The path in force on a page, by the rule of TeX's first mark: the first outlined
// heading on the page, else the last one before it, with the headings it sits under,
// as titles joined by " / ", each a link to its heading. The links inside an appendix
// heading's breadcrumb give way to the link of the heading itself, here and in the contents.
#let path-on-page() = {
  let page-number = here().page()
  let marks = query(heading.where(outlined: true).or(<contents>))
  let on-page = marks.filter(found => found.location().page() == page-number)
  let before = marks.filter(found => found.location().page() < page-number)
  let chosen = if on-page.len() > 0 { on-page.first() } else if before.len() > 0 { before.last() } else { none }

  if chosen == none { return none }

  let position = marks.position(found => found.location() == chosen.location())
  let trail = (chosen,)
  let level = chosen.level

  for found in marks.slice(0, position).rev() {
    if level == 1 { break }

    if found.level < level {
      trail.insert(0, found)
      level = found.level
    }
  }

  trail.map(found => link(found.location(), {
    show link: inner => inner.body
    found.body
  })).join(" / ")
}

#let running-header = context {
  if not has-cover and here().page() == 1 { return }

  grid(
    columns: (auto, 1fr),
    column-gutter: space.loose,
    align: (left + horizon, right + horizon),
    wordmark(width.running-wordmark),
    secondary(path-on-page()),
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
    if company != none { secondary[#company.name · #company.street · #company.city · #link("https://" + company.web)[#company.web]] },
    secondary(context [Page #counter(page).display("1 of 1", both: true)]),
  )
}

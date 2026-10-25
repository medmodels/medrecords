#import "style.typ": *
#import "numbers.typ": secondary
#import "references.typ": entry-label
#import "charts.typ": chart-style
#import "entries.typ": appendix, appendix-groups, collect, listing, render
#import "front.typ": contents-page, cover-block, cover-page, has-cover, running-footer, running-header
#import "details.typ": run-details-page

#let root = collect(report.entries, (), report.inputs)

#set document(
  title: report.name,
  author: if company == none { () } else { company.name },
  description: report.description,
)
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
#show: chart-style
#show title: set text(size: size.title, weight: "bold", fill: palette.navy)
#show heading: set block(above: space.wide, below: space.base)
#show heading: set text(fill: palette.navy, weight: "bold")
#show heading.where(level: 1): set text(size: size.section)
#show heading.where(level: 2): set text(size: size.subsection)
#show heading.where(level: 3): set text(size: size.minor)
#show heading.where(level: 4): set text(size: size.body)
#show heading.where(level: 5): set text(size: size.body, style: "italic")
#show heading: it => if it.level <= 5 { it } else { text(size: size.body, style: "italic", it) }
#show outline.entry.where(level: 1): set block(above: space.loose)
#show regex("\\S{" + str(longest-word) + ",}"): it => {
  it.text.clusters().chunks(word-piece).map(piece => piece.join()).join(sym.zws)
}

#if has-cover {
  cover-page()
  counter(page).update(1)
} else {
  cover-block()
}

#if root.leaves.len() > 0 {
  if has-cover { pagebreak(weak: true) }

  [#heading(level: 1, numbering: none)[Overview] #entry-label(())]
  listing(root.leaves, ())
}

#if options.contents { contents-page() }

#if report.entries.len() == 0 {
  block(width: 100%, above: space.base, below: 0pt, secondary[no entries])
}

#render(root, 1, (), true, listed: false)

#appendix(appendix-groups(report.entries, (), report.inputs))

#if options.run_details { run-details-page() }

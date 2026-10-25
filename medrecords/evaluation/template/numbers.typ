// Every number and single value the template prints.

#import "style.typ": *

#let secondary(body) = text(size: size.small, fill: palette.muted, body)

#let superscripts = (
  "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
  "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "−": "⁻", "-": "⁻",
)

#let superscript(number) = str(number).clusters().map(digit => superscripts.at(digit)).join()

// Digits in groups of three joined by a narrow no-break space, from five digits on.
#let grouped-digits(digits) = {
  if digits.len() < grouped-from { return digits }

  let head = calc.rem(digits.len(), 3)
  let groups = if head == 0 { () } else { (digits.slice(0, head),) }

  for start in range(head, digits.len(), step: 3) {
    groups.push(digits.slice(start, start + 3))
  }

  groups.join("\u{202F}")
}

#let sign-of(number) = if number < 0 { "−" } else { "" }

#let grouped(integer) = sign-of(integer) + grouped-digits(str(calc.abs(int(integer))))

// A number written with exactly the given decimals, its integer part grouped.
#let padded(value, places) = {
  let rounded = calc.round(calc.abs(value), digits: places)
  let shown = str(rounded)
  let (whole, fraction) = if shown.contains(".") { shown.split(".") } else { (shown, "") }
  let sign = if rounded == 0 { "" } else { sign-of(value) }

  if places == 0 { return sign + grouped-digits(whole) }

  sign + grouped-digits(whole) + "." + fraction + "0" * calc.max(0, places - fraction.len())
}

// "1.2 × 10¹²" for a magnitude from 10^12 on.
#let power-form(value) = {
  let exponent = calc.floor(calc.log(calc.abs(value)))
  let mantissa = calc.round(calc.abs(value) / calc.pow(10.0, exponent), digits: 1)

  if mantissa >= 10 {
    mantissa = mantissa / 10
    exponent += 1
  }

  sign-of(value) + str(mantissa) + " × 10" + superscript(exponent)
}

#let below-tiniest(value) = if value < 0 { "> −10" + superscript(-12) } else { "< 10" + superscript(-12) }

// Three significant digits below 0.001; places decimals otherwise.
#let fixed(value, places: decimals) = {
  let magnitude = calc.abs(value)

  if magnitude >= largest { return power-form(value) }

  if magnitude != 0 and magnitude < tiniest { return below-tiniest(value) }

  if magnitude != 0 and magnitude < smallest {
    return padded(value, significant-digits - calc.floor(calc.log(magnitude)) - 1)
  }

  padded(value, places)
}

// Three significant digits with the integer part always in full.
#let significant(value) = {
  let magnitude = calc.abs(value)

  if magnitude == 0 { return "0" }

  if magnitude >= largest { return power-form(value) }

  if magnitude < tiniest { return below-tiniest(value) }

  let exponent = calc.floor(calc.log(magnitude))
  let places = calc.max(0, significant-digits - exponent - 1)

  if calc.round(magnitude, digits: places) >= calc.pow(10.0, exponent + 1) {
    places = calc.max(0, places - 1)
  }

  padded(value, places)
}

// The shortest exact form of a number, its integer part grouped.
#let shortest(value) = {
  if type(value) == int { return grouped(value) }

  let magnitude = calc.abs(value)

  if magnitude >= largest { return power-form(value) }

  if magnitude != 0 and magnitude < tiniest { return below-tiniest(value) }

  let shown = str(magnitude)
  let (whole, fraction) = if shown.contains(".") { shown.split(".") } else { (shown, none) }

  sign-of(value) + grouped-digits(whole) + if fraction == none { "" } else { "." + fraction }
}

// The fewest decimals that write a number exactly, its integer part grouped.
#let exact(value) = {
  if calc.abs(value) >= largest { return power-form(value) }

  let tolerance = 1e-9 * calc.max(1, calc.abs(value))
  let places = range(13).find(places => calc.abs(calc.round(value, digits: places) - value) <= tolerance)

  padded(value, if places == none { 12 } else { places })
}

#let share(value) = padded(value * 100, 1) + "%"

#let points(value) = padded(value * 100, 1) + " pp"

#let unit-for(magnitude) = {
  if magnitude < 1 { "ms" } else if magnitude < seconds-per.minute { "s" } else if magnitude < seconds-per.hour {
    "min"
  } else if magnitude < seconds-per.day { "h" } else { "d" }
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

  if offset == "" { shown } else if offset == "+00:00" { shown + " UTC" } else { shown + " " + offset }
}

#let months = (
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
)

// "24 October 2026" for a timestamp.
#let day-of(stamp) = {
  let (year, month, day) = stamp.slice(0, 10).split("-")

  str(int(day)) + " " + months.at(int(month) - 1) + " " + year
}

#let kind-of(value) = if type(value) == dictionary { value.at("kind", default: none) }

#let is-duration(value) = kind-of(value) == "timedelta"

#let duration-seconds(value) = (
  value.days * seconds-per.day + value.seconds + value.microseconds * seconds-per.microsecond
)

#let duration-unit(values) = {
  let durations = values.filter(is-duration)

  if durations.len() == 0 { return auto }

  unit-for(calc.max(..durations.map(value => calc.abs(duration-seconds(value)))))
}

#let numeric(value) = type(value) in (int, float) or kind-of(value) in ("timedelta", "float")

#let is-whole(value) = type(value) == float and calc.abs(value) < largest and calc.fract(value) == 0

// The decimals of the floats of one column: none when every float is whole, else three.
#let column-decimals(values) = {
  let floats = values.filter(value => type(value) == float)

  if floats.len() > 0 and floats.all(is-whole) { 0 } else { decimals }
}

#let non-finite(value) = {
  if value.value == "nan" { "undefined" } else if value.value == "inf" { "infinity" } else { "minus infinity" }
}

// A single value: "none", "yes" or "no", a number, a date, a duration.
#let scalar(value, duration: auto, places: decimals, empty: none) = {
  if value == none {
    if empty == none { text(fill: palette.muted)[none] } else { empty }
  } else if type(value) == bool {
    if value { "yes" } else { "no" }
  } else if type(value) == int {
    grouped(value)
  } else if type(value) == float {
    fixed(value, places: places)
  } else if kind-of(value) == "timedelta" {
    seconds(duration-seconds(value), unit: duration)
  } else if kind-of(value) == "datetime" {
    let (date, time) = value.value.slice(0, 19).split("T")

    if time == "00:00:00" { date } else { date + " " + time }
  } else if kind-of(value) == "float" {
    non-finite(value)
  } else {
    str(value)
  }
}

// A parameter or summary value in its shortest exact form; lists joined by commas.
#let detail(value) = {
  let one(item) = if type(item) in (int, float) { shortest(item) } else { scalar(item) }

  if type(value) == array {
    if value.len() == 0 { text(fill: palette.muted)[none] } else { value.map(one).join(", ") }
  } else {
    one(value)
  }
}

// A category of counts: "missing" for a null value.
#let category(value) = {
  if value == none { text(fill: palette.muted, style: "italic")[missing] } else { scalar(value) }
}

#let in-unit(value, unit, duration: auto, places: decimals, empty: none) = {
  if unit == "share" and type(value) in (int, float) {
    share(value)
  } else if unit == "points" and type(value) in (int, float) {
    points(value)
  } else {
    scalar(value, duration: duration, places: places, empty: empty)
  }
}

// "3 rows", "1 row".
#let counted(number, noun) = grouped(number) + " " + noun + if number == 1 { "" } else { "s" }

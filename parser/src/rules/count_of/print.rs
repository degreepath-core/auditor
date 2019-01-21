use super::*;
use crate::traits::print::{self, Print};
use crate::util::result_to_option;
use crate::util::Oxford;

enum WhichUp {
	Course,
	Requirement,
}

fn print_and_collect(ref v: &[AnyRule]) -> Vec<String> {
	v.iter().map(|r| r.print_inner()).filter_map(result_to_option).collect()
}

fn print_and_join_for_block_elided(ref v: &[AnyRule]) -> String {
	v.iter()
		.map(|r| r.print_inner())
		.filter_map(result_to_option)
		.map(|r| format!("- {}", r))
		.collect::<Vec<String>>()
		.join("\n")
}

fn print_and_join_for_block_verbose(ref v: &[AnyRule]) -> String {
	v.iter()
		.map(|r| r.print_indented(1))
		.filter_map(result_to_option)
		.map(|r| format!("- {}", r))
		.collect::<Vec<String>>()
		.join("\n")
}

fn collect_and_sort_three_up(ref v: &[AnyRule]) -> (WhichUp, &AnyRule, &AnyRule, &AnyRule) {
	let a = &v[0];
	let b = &v[1];
	let c = &v[2];

	match v {
		[AnyRule::Course(_), AnyRule::Course(_), AnyRule::Requirement(_)] => (WhichUp::Course, a, b, c),
		[AnyRule::Course(_), AnyRule::Requirement(_), AnyRule::Course(_)] => (WhichUp::Course, a, c, b),
		[AnyRule::Requirement(_), AnyRule::Course(_), AnyRule::Course(_)] => (WhichUp::Course, b, c, a),
		[AnyRule::Course(_), AnyRule::Requirement(_), AnyRule::Requirement(_)] => (WhichUp::Requirement, a, b, c),
		[AnyRule::Requirement(_), AnyRule::Course(_), AnyRule::Requirement(_)] => (WhichUp::Requirement, b, a, c),
		[AnyRule::Requirement(_), AnyRule::Requirement(_), AnyRule::Course(_)] => (WhichUp::Requirement, c, a, b),
		_ => panic!("should only be triples of Course/Requirement, but was {:?}", v),
	}
}

impl print::Print for Rule {
	fn print(&self) -> print::Result {
		use std::fmt::Write;

		if self.is_single() {
			let req = &self.of[0].print_inner()?;
			if self.only_requirements() {
				return Ok(format!("complete the {} requirement", req));
			} else if self.only_courses() {
				return Ok(format!("take {}", req));
			} else {
				return Ok(format!("{}", req));
			}
		}

		if self.is_either() {
			let either = crate::rules::either::Rule {
				either: (Box::new(self.of[0].clone()), Box::new(self.of[1].clone())),
				surplus: None,
			};
			return either.print();
		}

		if self.is_both() {
			let both = crate::rules::both::Rule {
				both: (Box::new(self.of[0].clone()), Box::new(self.of[1].clone())),
				surplus: None,
			};
			return both.print();
		}

		let mut output = String::new();

		// assert: 2 < len

		if self.is_any() {
			if self.should_be_inline() {
				// assert: 2 < len < 4
				if self.only_requirements() {
					let rules = print_and_collect(&self.of);

					write!(
						&mut output,
						"complete one requirement from among {}",
						rules.oxford("or")
					)?;
				} else if self.only_courses() {
					let rules = print_and_collect(&self.of);

					write!(&mut output, "take one course from among {}", rules.oxford("or"))?;
				} else if self.only_courses_and_requirements() {
					let (which_up, a, b, c) = collect_and_sort_three_up(&self.of);
					let a = a.print_inner()?;
					let b = b.print_inner()?;
					let c = c.print_inner()?;

					match which_up {
						WhichUp::Course => {
							write!(&mut output, "take {} or {}, or complete the {} requirement", a, b, c)?
						}
						WhichUp::Requirement => write!(
							&mut output,
							"take {}, or complete either the {} or {} requirements",
							a, b, c
						)?,
					};
				} else {
					// force block mode due to clarify of mixed types and "any"
					let rules = print_and_join_for_block_verbose(&self.of);

					write!(&mut output, "do one of the following:\n\n{}", rules)?;
				}
			} else {
				// assert: 4 < len
				if self.only_requirements() {
					let rules = print_and_join_for_block_elided(&self.of);

					write!(&mut output, "complete one of the following requirements:\n\n{}", rules)?;
				} else if self.only_courses() {
					let rules = print_and_join_for_block_elided(&self.of);

					write!(&mut output, "take one of the following courses:\n\n{}", rules)?;
				} else {
					let rules = print_and_join_for_block_verbose(&self.of);

					write!(&mut output, "do one of the following:\n\n{}", rules)?;
				}
			}
		} else if self.is_all() {
			if self.should_be_inline() {
				// assert: 2 < len < 4
				if self.only_requirements() {
					let rules = print_and_collect(&self.of);

					write!(&mut output, "complete {}", rules.oxford("and"))?;
				} else if self.only_courses() {
					let rules = print_and_collect(&self.of);

					write!(&mut output, "take {}", rules.oxford("and"))?;
				} else if self.only_courses_and_requirements() {
					let (which_up, a, b, c) = collect_and_sort_three_up(&self.of);
					let a = a.print_inner()?;
					let b = b.print_inner()?;
					let c = c.print_inner()?;

					match which_up {
						WhichUp::Course => {
							write!(&mut output, "take {} and {}, and complete the {} requirement", a, b, c)?
						}
						WhichUp::Requirement => write!(
							&mut output,
							"take {}, and complete both the {} and {} requirements",
							a, b, c
						)?,
					};
				} else {
					// force block mode due to clarify of mixed types and "any"
					let rules = print_and_join_for_block_verbose(&self.of);

					write!(&mut output, "do all of the following:\n\n{}", rules)?;
				}
			} else {
				// assert: 4 < len
				if self.only_requirements() {
					let rules = print_and_join_for_block_elided(&self.of);

					write!(&mut output, "complete all of the following requirements:\n\n{}", rules)?;
				} else if self.only_courses() {
					let rules = print_and_join_for_block_elided(&self.of);

					write!(&mut output, "take all of the following courses:\n\n{}", rules)?;
				} else {
					let rules = print_and_join_for_block_verbose(&self.of);

					write!(&mut output, "do all of the following:\n\n{}", rules)?;
				}
			}
		} else {
			// numeric
			let n = self.count.english();

			if self.should_be_inline() {
				// assert: 2 < len < 4
				if self.only_requirements() {
					let rules = print_and_collect(&self.of);

					write!(
						&mut output,
						"complete {} requirements from among {}",
						n,
						rules.oxford("or")
					)?;
				} else if self.only_courses() {
					let rules = print_and_collect(&self.of);

					write!(&mut output, "take {} courses from among {}", n, rules.oxford("or"))?;
				} else if self.only_courses_and_requirements() {
					let (courses, reqs): (Vec<AnyRule>, Vec<AnyRule>) =
						self.of.clone().into_iter().partition(|r| match r {
							AnyRule::Course(_) => true,
							_ => false,
						});

					let mut rules: Vec<_> = vec![];
					rules.append(&mut print_and_collect(&courses));
					rules.append(&mut print_and_collect(&reqs));

					let rules = rules.oxford("or");

					write!(
						&mut output,
						"complete or take {} requirements or courses from among {}",
						n, rules
					)?;
				} else {
					// force block mode due to mixed content and numeric
					let rules = print_and_join_for_block_verbose(&self.of);

					write!(&mut output, "do {} from among the following:\n\n{}", n, rules)?;
				}
			} else {
				// assert: 4 < len
				if self.only_requirements() {
					let rules = print_and_join_for_block_elided(&self.of);

					write!(
						&mut output,
						"complete {} from among the following requirements:\n\n{}",
						n, rules
					)?;
				} else if self.only_courses() {
					let rules = print_and_join_for_block_elided(&self.of);

					write!(&mut output, "take {} of the following courses:\n\n{}", n, rules)?;
				} else {
					let rules = print_and_join_for_block_verbose(&self.of);

					write!(&mut output, "do {} from among the following:\n\n{}", n, rules)?;
				}
			}
		}

		Ok(output)
	}
}

use super::*;
use crate::rules::req_ref;
use crate::traits::print::Print;

#[test]
fn serialize() {
	let input = Rule {
		either: (
			Box::new(AnyRule::Requirement(req_ref::Rule {
				requirement: String::from("Name"),
				optional: false,
			})),
			Box::new(AnyRule::Requirement(req_ref::Rule {
				requirement: String::from("Name 2"),
				optional: false,
			})),
		),
		surplus: None,
	};

	let expected_str = "---
either:
  - requirement: Name
    optional: false
  - requirement: Name 2
    optional: false
surplus: ~";

	let actual = serde_yaml::to_string(&input).unwrap();
	assert_eq!(actual, expected_str);
}

#[test]
fn deserialize() {
	let input = "---
either:
  - requirement: Name
    optional: false
  - requirement: Name 2
    optional: false
surplus: ~";

	let expected_struct = Rule {
		either: (
			Box::new(AnyRule::Requirement(req_ref::Rule {
				requirement: String::from("Name"),
				optional: false,
			})),
			Box::new(AnyRule::Requirement(req_ref::Rule {
				requirement: String::from("Name 2"),
				optional: false,
			})),
		),
		surplus: None,
	};

	let actual: Rule = serde_yaml::from_str(&input).unwrap();
	assert_eq!(actual, expected_struct);
}

#[test]
fn pretty_print() {
	let input: Rule = serde_yaml::from_str(&"{either: [{requirement: A}, {requirement: B}]}").unwrap();
	let expected = "complete either the “A” or “B” requirement";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule = serde_yaml::from_str(&"{either: [CS 111, CS 121]}").unwrap();
	let expected = "take either CS 111 or CS 121";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule = serde_yaml::from_str(&"{either: [CS 121, {requirement: A}]}").unwrap();
	let expected = "take CS 121 or complete the “A” requirement";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule = serde_yaml::from_str(&"{either: [{requirement: A}, CS 121]}").unwrap();
	let expected = "complete the “A” requirement or take CS 121";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule = serde_yaml::from_str(&"{either: [CS 121, {either: [CS 251, CS 130]}]}").unwrap();
	let expected = "either take CS 121 or take either CS 251 or CS 130";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule = serde_yaml::from_str(&"{either: [{requirement: A}, {either: [CS 251, CS 130]}]}").unwrap();
	let expected = "either complete the “A” requirement or take either CS 251 or CS 130";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule =
		serde_yaml::from_str(&"{either: [{given: courses, what: courses, do: count >= 3}, CS 121]}").unwrap();
	let expected = "either take at least three courses or take CS 121";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule =
		serde_yaml::from_str(&"{either: [{given: courses, what: courses, do: count >= 3}, {requirement: A}]}").unwrap();
	let expected = "either take at least three courses or complete the “A” requirement";
	assert_eq!(expected, input.print().unwrap());

	let input: Rule = serde_yaml::from_str(&"{either: [{given: courses, what: courses, do: count >= 3}, {given: these courses, courses: [THEAT 233], repeats: all, what: courses, do: count >= 4}]}").unwrap();
	let expected = "either:

- take at least three courses

- or take THEAT 233 at least four times";
	assert_eq!(expected, input.print().unwrap());
}

use super::Requirement;
use crate::rules::Rule;
use crate::rules::{given, req_ref};
use crate::save::SaveBlock;
use crate::{filter, rules, value};
use maplit::btreemap;

#[test]
fn serialize() {
	let data = Requirement {
		name: String::from("a requirement"),
		message: None,
		department_audited: false,
		registrar_audited: false,
		result: Some(Rule::Requirement(req_ref::Rule {
			requirement: String::from("name"),
			optional: false,
		})),
		contract: false,
		save: vec![],
		requirements: vec![],
	};

	let expected = "---
name: a requirement
message: ~
department_audited: false
result:
  requirement: name
  optional: false
contract: false
registrar_audited: false
save: []
requirements: []";

	let actual = serde_yaml::to_string(&data).unwrap();
	assert_eq!(actual, expected);
}

#[test]
fn deserialize() {
	let data = "---
name: a requirement
message: ~
department_audited: false
registrar_audited: false
result:
  requirement: name
  optional: false
contract: false
save: []
requirements: []";

	let expected = Requirement {
		name: String::from("a requirement"),
		message: None,
		department_audited: false,
		registrar_audited: false,
		result: Some(Rule::Requirement(req_ref::Rule {
			requirement: String::from("name"),
			optional: false,
		})),
		contract: false,
		save: vec![],
		requirements: vec![],
	};

	let actual: Requirement = serde_yaml::from_str(&data).unwrap();
	assert_eq!(actual, expected);
}

#[test]
fn deserialize_with_defaults() {
	let data = "---
name: a requirement
message: ~
result: {requirement: name, optional: false}";

	let expected = Requirement {
		name: String::from("a requirement"),
		message: None,
		department_audited: false,
		registrar_audited: false,
		result: Some(Rule::Requirement(req_ref::Rule {
			requirement: String::from("name"),
			optional: false,
		})),
		contract: false,
		save: vec![],
		requirements: vec![],
	};

	let actual: Requirement = serde_yaml::from_str(&data).unwrap();
	assert_eq!(actual, expected);
}

#[test]
fn deserialize_message_only() {
	let data = "---
name: a requirement
message: a message";

	let expected = Requirement {
		name: String::from("a requirement"),
		message: Some("a message".to_string()),
		department_audited: false,
		registrar_audited: false,
		result: None,
		contract: false,
		save: vec![],
		requirements: vec![],
	};

	let actual: Requirement = serde_yaml::from_str(&data).unwrap();
	assert_eq!(actual, expected);
}

#[test]
fn deserialize_ba_interim() {
	let data = "---
name: a requirement
save:
  - given: courses
    where: {semester: Interim}
    what: courses
    name: Interim Courses
result:
  both:
    - {given: save, save: Interim Courses, what: credits, do: sum >= 3}
    - {given: save, save: Interim Courses, what: courses, do: count >= 3}";

	let expected_filter: filter::Clause = btreemap! {
		"semester".into() => "Interim".parse::<value::WrappedValue>().unwrap(),
	};

	let expected = Requirement {
		name: String::from("a requirement"),
		message: None,
		department_audited: false,
		registrar_audited: false,
		result: Some(Rule::Both(rules::both::Rule {
			both: (
				Box::new(Rule::Given(given::Rule {
					given: given::Given::NamedVariable {
						save: "Interim Courses".to_string(),
						what: given::GivenCoursesWhatOptions::Credits,
					},
					limit: None,
					filter: None,
					action: "sum >= 3".parse().unwrap(),
				})),
				Box::new(Rule::Given(given::Rule {
					given: given::Given::NamedVariable {
						save: "Interim Courses".to_string(),
						what: given::GivenCoursesWhatOptions::Courses,
					},
					limit: None,
					filter: None,
					action: "count >= 3".parse().unwrap(),
				})),
			),
		})),
		contract: false,
		save: vec![SaveBlock {
			name: "Interim Courses".to_string(),
			given: given::GivenForSaveBlock::AllCourses {
				what: given::GivenCoursesWhatOptions::Courses,
			},
			limit: None,
			filter: Some(expected_filter),
			action: None,
		}],
		requirements: vec![],
	};

	let actual: Requirement = serde_yaml::from_str(&data).unwrap();
	assert_eq!(actual, expected);
}

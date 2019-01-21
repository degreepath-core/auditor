use super::TaggedValue;
use super::Value;
use crate::action::Operator;
use crate::traits::print;
use crate::util::{self, Oxford};
use std::fmt;
use std::str::FromStr;

#[derive(Debug, PartialEq, Serialize, Deserialize, Clone)]
pub enum WrappedValue {
	Single(TaggedValue),
	Or(Vec<TaggedValue>),
	And(Vec<TaggedValue>),
}

impl WrappedValue {
	pub fn new(s: &str) -> Self {
		WrappedValue::Single(TaggedValue {
			op: Operator::EqualTo,
			value: Value::String(s.to_string()),
		})
	}

	pub fn is_true(&self) -> bool {
		match &self {
			WrappedValue::Single(val) => val.is_true(),
			_ => false,
		}
	}
}

impl print::Print for WrappedValue {
	fn print(&self) -> print::Result {
		match &self {
			WrappedValue::Single(v) => Ok(format!("{}", v.print()?)),
			WrappedValue::Or(v) | WrappedValue::And(v) => {
				let v: Vec<String> = v
					.iter()
					.filter_map(|r| match r.print() {
						Ok(p) => Some(p),
						Err(_) => None,
					})
					.collect();

				return match &self {
					WrappedValue::Or(_) => Ok(v.oxford("or")),
					WrappedValue::And(_) => Ok(v.oxford("and")),
					_ => panic!("we already checked for Single"),
				};
			}
		}
	}
}

impl FromStr for WrappedValue {
	type Err = util::ParseError;

	fn from_str(s: &str) -> Result<Self, Self::Err> {
		let parts: Vec<_> = s.split(" | ").collect();

		if parts.len() > 1 {
			let mut tagged = Vec::with_capacity(parts.len());
			for part in parts {
				tagged.push(part.parse::<TaggedValue>()?);
			}

			return Ok(WrappedValue::Or(tagged));
		}

		let parts: Vec<_> = s.split(" & ").collect();
		if parts.len() > 1 {
			let mut tagged = Vec::with_capacity(parts.len());
			for part in parts {
				tagged.push(part.parse::<TaggedValue>()?);
			}

			return Ok(WrappedValue::And(tagged));
		}

		Ok(WrappedValue::Single(s.parse::<TaggedValue>()?))
	}
}

impl fmt::Display for WrappedValue {
	fn fmt(&self, fmt: &mut fmt::Formatter) -> fmt::Result {
		let desc = match &self {
			WrappedValue::Single(val) => format!("{}", val),
			WrappedValue::And(values) | WrappedValue::Or(values) => {
				let parts: Vec<_> = values.iter().map(|v| format!("{}", v)).collect();

				match &self {
					WrappedValue::And(_) => parts.join(" & "),
					WrappedValue::Or(_) => parts.join(" | "),
					_ => panic!("we already checked for Single"),
				}
			}
		};
		fmt.write_str(&desc)
	}
}
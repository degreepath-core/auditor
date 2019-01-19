use crate::rules::Rule;
use crate::save::SaveBlock;
use crate::util;
use std::collections::BTreeMap;

#[cfg(test)]
mod tests;

#[derive(Debug, PartialEq, Serialize, Deserialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct Requirement {
	#[serde(default)]
	pub message: Option<String>,
	#[serde(default = "util::serde_false")]
	pub department_audited: bool,
	#[serde(default)]
	pub result: Option<Rule>,
	#[serde(default = "util::serde_false")]
	pub contract: bool,
	#[serde(default)]
	pub save: Vec<SaveBlock>,
	#[serde(default)]
	pub requirements: BTreeMap<String, Requirement>,
}
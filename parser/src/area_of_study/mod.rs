use crate::requirement::Requirement;
use crate::rules::Rule;
use indexmap::IndexMap;

mod attributes;

#[cfg(test)]
mod tests;

#[derive(Debug, PartialEq, Serialize, Deserialize, Clone)]
pub struct AreaOfStudy {
	#[serde(rename = "name")]
	pub area_name: String,
	#[serde(flatten)]
	pub area_type: AreaType,
	pub catalog: String,
	pub result: Rule,
	pub requirements: IndexMap<String, Requirement>,
	#[serde(default)]
	pub attributes: Option<attributes::Attributes>,
}

#[derive(Debug, PartialEq, Serialize, Deserialize, Clone)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum AreaType {
	Degree,
	Major { degree: String },
	Minor { degree: String },
	Concentration { degree: String },
	Emphasis { degree: String, major: String },
}

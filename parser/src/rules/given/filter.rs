use crate::util;
use serde::de::{Deserialize, Deserializer};
use serde::ser::{Serialize, Serializer};

use super::action;
use crate::rules::given::action::ParseError;

use std::collections::HashMap;
use std::fmt;
use std::str::FromStr;

pub type Clause = HashMap<String, WrappedValue>;

pub fn deserialize_with<'de, D>(deserializer: D) -> Result<Option<Clause>, D::Error>
where
    D: Deserializer<'de>,
{
    #[derive(Deserialize)]
    struct Wrapper(#[serde(deserialize_with = "util::string_or_struct_parseerror")] WrappedValue);

    // TODO: improve this to not transmute the hashmap right after creation
    let v: Result<HashMap<String, Wrapper>, D::Error> = HashMap::deserialize(deserializer);

    match v {
        Ok(v) => {
            let transmuted: Clause = v.iter().map(|(k, v)| (k.clone(), v.0.clone())).collect();
            Ok(Some(transmuted))
        }
        Err(err) => Err(err),
    }
}

#[derive(Debug, PartialEq, Deserialize, Clone)]
pub enum WrappedValue {
    Single(TaggedValue),
    Or([TaggedValue; 2]),
    And([TaggedValue; 2]),
}

impl WrappedValue {
    pub fn is_true(&self) -> bool {
        match &self {
            WrappedValue::Single(val) => val.is_true(),
            _ => false,
        }
    }
}

impl FromStr for WrappedValue {
    type Err = ParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let or_bits: Vec<_> = s.split(" | ").collect();
        match or_bits.as_slice() {
            [a, b] => {
                return Ok(WrappedValue::Or([
                    a.parse::<TaggedValue>()?,
                    b.parse::<TaggedValue>()?,
                ]))
            }
            _ => (),
        };

        let and_bits: Vec<_> = s.split(" & ").collect();
        match and_bits.as_slice() {
            [a, b] => {
                return Ok(WrappedValue::And([
                    a.parse::<TaggedValue>()?,
                    b.parse::<TaggedValue>()?,
                ]))
            }
            _ => (),
        };

        Ok(WrappedValue::Single(s.parse::<TaggedValue>()?))
    }
}

impl fmt::Display for WrappedValue {
    fn fmt(&self, fmt: &mut fmt::Formatter) -> fmt::Result {
        let desc = match &self {
            WrappedValue::And([a, b]) => format!("{} & {}", a, b),
            WrappedValue::Or([a, b]) => format!("{} | {}", a, b),
            WrappedValue::Single(val) => format!("{}", val),
        };
        fmt.write_str(&desc)
    }
}

impl Serialize for WrappedValue {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&format!("{}", &self))
    }
}

#[derive(Debug, PartialEq, Deserialize, Clone)]
pub struct TaggedValue {
    pub op: action::Operator,
    pub value: Value,
}

impl TaggedValue {
    pub fn is_true(&self) -> bool {
        match &self.op {
            action::Operator::EqualTo => self.value == true,
            _ => false,
        }
    }
}

impl FromStr for TaggedValue {
    type Err = ParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.get(0..1) {
            Some("!") | Some("<") | Some(">") | Some("=") => {
                let splitted: Vec<_> = s.split_whitespace().collect();

                match splitted.as_slice() {
                    [value] => {
                        let value = value.parse::<Value>()?;

                        Ok(TaggedValue {
                            op: action::Operator::EqualTo,
                            value,
                        })
                    }
                    [op, value] => {
                        let op = op.parse::<action::Operator>()?;
                        let value = value.parse::<Value>()?;

                        Ok(TaggedValue { op, value })
                    }
                    _ => {
                        // println!("{:?}", splitted);
                        Err(ParseError::InvalidAction)
                    }
                }
            }
            _ => {
                let value = s.parse::<Value>()?;

                Ok(TaggedValue {
                    op: action::Operator::EqualTo,
                    value,
                })
            }
        }
    }
}

impl fmt::Display for TaggedValue {
    fn fmt(&self, fmt: &mut fmt::Formatter) -> fmt::Result {
        let desc = format!("{} {}", self.op, self.value);
        fmt.write_str(&desc)
    }
}

impl Serialize for TaggedValue {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&format!("{}", &self))
    }
}

#[derive(Debug, PartialEq, Deserialize, Clone)]
pub enum Constant {
    #[serde(rename = "graduation-year")]
    GraduationYear,
}

impl fmt::Display for Constant {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match &self {
            Constant::GraduationYear => write!(f, "graduation-year"),
        }
    }
}

impl FromStr for Constant {
    type Err = ParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let s = s.trim();

        match s {
            "graduation-year" => Ok(Constant::GraduationYear),
            _ => Err(ParseError::UnknownCommand),
        }
    }
}

impl Serialize for Constant {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&format!("{}", &self))
    }
}

#[derive(Debug, PartialEq, Deserialize, Clone)]
pub enum Value {
    Constant(Constant),
    Bool(bool),
    Integer(u64),
    Float(f64),
    String(String),
}

impl From<String> for Value {
    fn from(s: String) -> Value {
        Value::String(s)
    }
}

impl From<&str> for Value {
    fn from(s: &str) -> Value {
        Value::String(s.to_string())
    }
}

impl From<u64> for Value {
    fn from(i: u64) -> Value {
        Value::Integer(i)
    }
}

impl From<bool> for Value {
    fn from(b: bool) -> Value {
        Value::Bool(b)
    }
}

impl FromStr for Value {
    type Err = ParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        if let Ok(constant) = s.parse::<Constant>() {
            return Ok(Value::Constant(constant));
        }

        if let Ok(num) = s.parse::<u64>() {
            return Ok(Value::Integer(num));
        }

        if let Ok(num) = s.parse::<f64>() {
            return Ok(Value::Float(num));
        }

        if let Ok(b) = s.parse::<bool>() {
            return Ok(Value::Bool(b));
        }

        Ok(Value::String(s.to_string()))
    }
}

impl PartialEq<bool> for Value {
    fn eq(&self, rhs: &bool) -> bool {
        match &self {
            Value::Bool(b) => b == rhs,
            _ => false,
        }
    }
}

impl fmt::Display for Value {
    fn fmt(&self, fmt: &mut fmt::Formatter) -> fmt::Result {
        let desc = match &self {
            Value::String(s) => format!("{}", s),
            Value::Integer(n) => format!("{}", n),
            Value::Float(n) => format!("{:.2}", n),
            Value::Bool(b) => format!("{}", b),
            Value::Constant(s) => format!("{}", s),
        };
        fmt.write_str(&desc)
    }
}

impl Serialize for Value {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&format!("{}", &self))
    }
}

#[cfg(test)]
mod tests {
    use super::super::action::Operator;
    use super::*;

    #[test]
    fn serialize_simple() {
        let data: Clause = hashmap! {
            "level".into() => "100".parse::<WrappedValue>().unwrap(),
        };

        let expected = r#"---
level: "= 100""#;

        let actual = serde_yaml::to_string(&data).unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn serialize_or() {
        let data: Clause = hashmap! {
            "level".into() => "100 | 200".parse::<WrappedValue>().unwrap(),
        };

        let expected = r#"---
level: "= 100 | = 200""#;

        let actual = serde_yaml::to_string(&data).unwrap();
        assert_eq!(actual, expected);

        let data: Clause = hashmap! {
            "level".into() =>  "< 100 | 200".parse::<WrappedValue>().unwrap(),
        };

        let expected = r#"---
level: "< 100 | = 200""#;

        let actual = serde_yaml::to_string(&data).unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_value_str() {
        let data = "FYW";
        let expected = Value::String("FYW".into());
        let actual: Value = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_value_int() {
        let data = "1";
        let expected = Value::Integer(1);
        let actual: Value = data.parse().unwrap();
        assert_eq!(actual, expected);

        let data = "100";
        let expected = Value::Integer(100);
        let actual: Value = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_value_float() {
        let data = "1.0";
        let expected = Value::Float(1.0);
        let actual: Value = data.parse().unwrap();
        assert_eq!(actual, expected);

        let data = "1.5";
        let expected = Value::Float(1.5);
        let actual: Value = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_value_bool() {
        let data = "true";
        let expected = Value::Bool(true);
        let actual: Value = data.parse().unwrap();
        assert_eq!(actual, expected);

        let data = "false";
        let expected = Value::Bool(false);
        let actual: Value = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_tagged_value_untagged() {
        let data = "FYW";
        let expected = TaggedValue {
            op: Operator::EqualTo,
            value: Value::String("FYW".into()),
        };
        let actual: TaggedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_tagged_value_eq() {
        let data = "= FYW";
        let expected = TaggedValue {
            op: Operator::EqualTo,
            value: Value::String("FYW".into()),
        };
        let actual: TaggedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_tagged_value_neq() {
        let data = "! FYW";
        let expected = TaggedValue {
            op: Operator::NotEqualTo,
            value: Value::String("FYW".into()),
        };
        let actual: TaggedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_tagged_value_gt() {
        let data = "> FYW";
        let expected = TaggedValue {
            op: Operator::GreaterThan,
            value: Value::String("FYW".into()),
        };
        let actual: TaggedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_tagged_value_gte() {
        let data = ">= FYW";
        let expected = TaggedValue {
            op: Operator::GreaterThanEqualTo,
            value: Value::String("FYW".into()),
        };
        let actual: TaggedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_tagged_value_lt() {
        let data = "< FYW";
        let expected = TaggedValue {
            op: Operator::LessThan,
            value: Value::String("FYW".into()),
        };
        let actual: TaggedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_tagged_value_lte() {
        let data = "<= FYW";
        let expected = TaggedValue {
            op: Operator::LessThanEqualTo,
            value: Value::String("FYW".into()),
        };
        let actual: TaggedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_wrapped_value() {
        let data = "FYW";
        let expected = WrappedValue::Single(TaggedValue {
            op: Operator::EqualTo,
            value: Value::String("FYW".into()),
        });
        let actual: WrappedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_wrapped_value_ne() {
        let data = "! FYW";
        let expected = WrappedValue::Single(TaggedValue {
            op: Operator::NotEqualTo,
            value: Value::String("FYW".into()),
        });
        let actual: WrappedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_wrapped_value_or_ne() {
        let data = "! FYW | = FYW";
        let expected = WrappedValue::Or([
            TaggedValue {
                op: Operator::NotEqualTo,
                value: Value::String("FYW".into()),
            },
            TaggedValue {
                op: Operator::EqualTo,
                value: Value::String("FYW".into()),
            },
        ]);
        let actual: WrappedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_wrapped_value_or_untagged() {
        let data = "FYW | FYW";
        let expected = WrappedValue::Or([
            TaggedValue {
                op: Operator::EqualTo,
                value: Value::String("FYW".into()),
            },
            TaggedValue {
                op: Operator::EqualTo,
                value: Value::String("FYW".into()),
            },
        ]);
        let actual: WrappedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_wrapped_value_and_untagged() {
        let data = "FYW & FYW";
        let expected = WrappedValue::And([
            TaggedValue {
                op: Operator::EqualTo,
                value: Value::String("FYW".into()),
            },
            TaggedValue {
                op: Operator::EqualTo,
                value: Value::String("FYW".into()),
            },
        ]);
        let actual: WrappedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_wrapped_value_and_ne() {
        let data = "! FYW & = FYW";
        let expected = WrappedValue::And([
            TaggedValue {
                op: Operator::NotEqualTo,
                value: Value::String("FYW".into()),
            },
            TaggedValue {
                op: Operator::EqualTo,
                value: Value::String("FYW".into()),
            },
        ]);
        let actual: WrappedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn deserialize_wrapped_value_multiword_single_value() {
        let data = "St. Olaf College";
        let expected = WrappedValue::Single(TaggedValue {
            op: Operator::EqualTo,
            value: Value::String("St. Olaf College".into()),
        });
        let actual: WrappedValue = data.parse().unwrap();
        assert_eq!(actual, expected);
    }
}
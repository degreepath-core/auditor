use crate::audit::AuditResult;
use crate::path::Path;
use crate::rule::{Rule, RuleStatus};
use crate::student::Student;
use crate::to_prose::{ProseOptions, ToProse};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct CountRule {
    pub count: usize,
    pub audit_status: RuleStatus,
    pub audit: Vec<AuditResult>,
    pub items: Vec<Box<Rule>>,
    pub max_rank: String,
    pub path: Path,
    pub rank: String,
    pub status: RuleStatus,
}

impl CountRule {
    pub fn all_items_are_requirements(&self) -> bool {
        self.items.iter().all(|r| match r.as_ref() {
            Rule::Requirement(_) => true,
            _ => false,
        })
    }
}

impl ToProse for CountRule {
    fn to_prose(
        &self,
        f: &mut std::fmt::Formatter<'_>,
        student: &Student,
        options: &ProseOptions,
        indent: usize,
    ) -> std::fmt::Result {
        if options.show_paths {
            write!(f, "{}", " ".repeat(indent * 4))?;
            writeln!(f, "path: {}", self.path)?;
        };

        if options.show_ranks {
            write!(f, "{}", " ".repeat(indent * 4))?;
            writeln!(
                f,
                "rank({2}): {0} of {1}",
                self.rank,
                self.max_rank,
                if self.status.is_passing() { "t" } else { "f" }
            )?;
        };

        write!(f, "{}", " ".repeat(indent * 4))?;
        writeln!(f, "status: {:?}", self.status)?;

        write!(f, "{}", " ".repeat(indent * 4))?;
        let size = self.items.len();

        if self.count == 1 && size == 2 {
            write!(f, "either of (these 2)")?;
        } else if self.count == 2 && size == 2 {
            write!(f, "both of (these 2)")?;
        } else if (self.count as usize) == size {
            write!(f, "all of (these {})", size)?;
        } else if self.count == 2 {
            write!(f, "any of (these {})", size)?;
        } else {
            write!(f, "at least {} of {}", self.count, size)?;
        }

        let ok_count = self
            .items
            .iter()
            .filter(|r| r.status().is_passing())
            .count();

        write!(f, " (ok: {}, need: {})", ok_count, self.count)?;

        writeln!(f)?;

        if !self.audit.is_empty() {
            write!(f, "{}", " ".repeat(indent * 4))?;
            writeln!(
                f,
                "This requirement has a post-audit [status={:?}]",
                self.audit_status
            )?;

            write!(f, "{}", " ".repeat((indent + 1) * 4))?;
            writeln!(f, "There must be:")?;

            for (i, a) in self.audit.iter().enumerate() {
                writeln!(f, "{}.", i + 1)?;
                a.to_prose(f, student, options, indent + 2)?;
            }

            writeln!(f)?;
        }

        for (i, r) in self.items.iter().enumerate() {
            write!(f, "{}", " ".repeat((indent + 1) * 4))?;
            writeln!(f, "{}.", i + 1)?;

            r.to_prose(f, student, options, indent + 2)?;

            if size != 2 && i < self.items.len() - 1 {
                writeln!(f)?;
            }
        }

        Ok(())
    }
}

use crate::to_record::{Record, RecordOptions, RecordStatus, ToRecord};
impl ToRecord for CountRule {
    fn get_row(&self, student: &Student, options: &RecordOptions, is_waived: bool) -> Vec<Record> {
        let mut row: Vec<Record> = Vec::new();

        let is_waived = is_waived || self.status.is_waived();

        let show_prefix = !self.all_items_are_requirements();

        if self.count == 1 {
            let item = self.items.iter().find(|r| r.status().is_passing());

            match item {
                Some(item) => {
                    for sub_record in item.get_row(student, options, is_waived) {
                        row.push(Record {
                            title: "1 of these".to_string(),
                            subtitle: None,
                            status: RecordStatus::Waived,
                            content: sub_record.content,
                        });
                    }
                }
                _ if is_waived => {
                    row.push(Record {
                        title: "1 of these".to_string(),
                        subtitle: None,
                        status: RecordStatus::Waived,
                        content: vec![],
                    });
                }
                _ => {
                    row.push(Record {
                        title: "1 of these".to_string(),
                        subtitle: None,
                        status: RecordStatus::Empty,
                        content: vec![],
                    });
                }
            }
        } else {
            for (i, item) in self.items.iter().enumerate() {
                let text = format!("#{}", i + 1);
                for sub_record in item.get_row(student, options, is_waived) {
                    if show_prefix {
                        row.push(Record {
                            title: format!("{} -> {}", text, sub_record.title),
                            subtitle: sub_record.subtitle,
                            status: *item.status(),
                            content: sub_record.content,
                        });
                    } else if item.status().is_waived() {
                        row.push(Record {
                            title: sub_record.title,
                            subtitle: sub_record.subtitle,
                            status: RecordStatus::Waived,
                            content: vec![],
                        });
                    } else if sub_record.content.is_empty() {
                        row.push(Record {
                            title: sub_record.title,
                            subtitle: sub_record.subtitle,
                            status: RecordStatus::Empty,
                            content: vec![],
                        });
                    } else {
                        row.push(Record {
                            title: sub_record.title,
                            subtitle: sub_record.subtitle,
                            status: *item.status(),
                            content: sub_record.content,
                        });
                    }
                }
            }
        }

        row
    }

    fn get_requirements(&self) -> Vec<String> {
        self.items
            .iter()
            .flat_map(|r| r.get_requirements())
            .collect()
    }
}

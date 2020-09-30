use crate::path::Path;
use crate::rule::RuleStatus;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Serialize, Deserialize, Debug)]
pub struct Student {
    pub areas: Vec<AreaOfStudy>,
    pub catalog: String,
    pub courses: Vec<Course>,
    pub covid: Option<bool>,
    pub current_term: String,
    pub curriculum: String,
    // pub exceptions: Vec<Exception>,
    pub matriculation: String,
    pub mediums: StudentPerformingMediums,
    pub organizations: Vec<StudentOrganization>,
    pub performance_attendances: Vec<Attendance>,
    pub performances: Vec<Performance>,
    // pub proficiencies: StudentProficiencies,
    pub stnum: String,
    // pub templates: BTreeMap<String, String>, // todo: type this accurately
}

impl Student {
    pub fn get_class_by_clbid(&self, clbid: &ClassLabId) -> Option<&Course> {
        self.courses.iter().find(|c| c.clbid == *clbid)
    }
}

#[derive(Serialize, Deserialize, Debug)]
pub struct StudentOrganization {
    pub dept: String,
    pub id: String,
    pub instrument: Option<String>,
    pub role: String,
    pub name: String,
    pub term: String,
    pub year: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Attendance {
    pub id: String,
    pub name: String,
    pub term: String,
    pub year: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Performance {
    pub id: String,
    pub name: String,
    pub term: String,
    pub year: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct StudentPerformingMediums {
    pub ppm: String,
    pub ppm2: String,
    pub spm: String,
    pub spm2: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub enum StudentProficiencyType {
    Y,
    C,
    N,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct StudentProficiencies {
    pub guitar: StudentProficiencyType,
    pub keyboard_1: StudentProficiencyType,
    pub keyboard_2: StudentProficiencyType,
    pub keyboard_3: StudentProficiencyType,
    pub keyboard_4: StudentProficiencyType,
}

#[derive(Serialize, Deserialize, Debug, Clone, Ord, PartialOrd, Eq, PartialEq)]
pub struct ClassLabId(String);

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct CourseId(String);

#[derive(Serialize, Deserialize, Debug)]
pub struct Course {
    pub attributes: BTreeSet<String>,
    pub clbid: ClassLabId,
    pub course: String,
    pub course_type: String,
    pub credits: String,
    pub crsid: CourseId,
    pub flag_gpa: bool,
    pub flag_in_progress: bool,
    pub flag_incomplete: bool,
    pub flag_individual_major: bool,
    pub flag_repeat: bool,
    pub flag_stolaf: bool,
    pub gereqs: BTreeSet<String>,
    pub grade_code: String,
    pub grade_option: String,
    pub grade_points: String,
    pub grade_points_gpa: String,
    pub institution_name: String,
    pub institution_short: String,
    pub level: f64,
    pub name: String,
    pub number: String,
    // pub schedid: String,
    pub section: Option<String>,
    pub sub_type: String,
    pub subject: String,
    pub term: String,
    pub transcript_code: String,
    pub transcript_code_long: String,
    pub year: String,
}

impl Course {
    pub fn verbose(&self) -> String {
        if self.institution_short == "STOLAF" {
            format!(
                "{} \"{}\" {} {:?} #{:?}",
                self.course_with_term(),
                self.name,
                self.credits,
                self.grade_code,
                self.clbid
            )
        } else {
            format!(
                "{} \"{}\" [{}] {} {:?} #{:?}",
                self.course_with_term(),
                self.name,
                self.institution_short,
                self.credits,
                self.grade_code,
                self.clbid
            )
        }
    }

    pub fn semi_verbose(&self) -> String {
        if self.institution_short == "STOLAF" {
            format!("{}", self.course_with_term())
        } else {
            format!("[{}] {}", self.institution_short, self.course_with_term())
        }
    }

    pub fn course_with_term(&self) -> String {
        let label = if self.number == "" {
            format!("\"{}\"", self.name,)
        } else {
            let suffix = match self.sub_type.as_str() {
                "lab" => ".L",
                "flac" => ".F",
                "discussion" => ".D",
                _ => "",
            };

            format!(
                "{}{}{}",
                self.number,
                self.section.clone().unwrap_or("".into()),
                suffix
            )
        };

        format!("{} {} {}", self.subject, label, self.year_term())
    }

    fn year_term(&self) -> String {
        format!("{}-{}", self.year, self.term)
    }

    pub fn calculate_symbol(&self, status: &RuleStatus) -> &'static str {
        if *status == RuleStatus::Waived {
            "[ovr]"
        } else if self.flag_incomplete {
            "[dnf]"
        } else if self.flag_in_progress {
            "[ip?]"
        } else if self.flag_repeat {
            "[rep]"
        } else {
            "[ ok]"
        }
    }
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(tag = "type")]
pub enum Exception {
    #[serde(rename = "insert")]
    Insert {
        path: Path,
        area_code: String,
        clbid: ClassLabId,
    },
    #[serde(rename = "force-insert")]
    ForceInsert {
        path: Path,
        area_code: String,
        clbid: ClassLabId,
    },
    #[serde(rename = "override")]
    Override {
        path: Path,
        area_code: String,
        clbid: ClassLabId,
    },
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(tag = "kind")]
pub enum AreaOfStudy {
    #[serde(rename = "degree")]
    Degree(Degree),
    #[serde(rename = "major")]
    Major(Major),
    #[serde(rename = "concentration")]
    Concentration(Concentration),
    #[serde(rename = "emphasis")]
    Emphasis(Emphasis),
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Degree {
    pub code: String,
    pub degree: String,
    pub gpa: String,
    pub name: String,
    pub status: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Major {
    pub code: String,
    pub degree: String,
    pub dept: String,
    pub name: String,
    pub status: String,
    // pub terms_since_declaration: u32,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Concentration {
    pub code: String,
    pub degree: String,
    pub dept: String,
    pub name: String,
    pub status: String,
    // pub terms_since_declaration: u32,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Emphasis {
    pub code: String,
    pub degree: String,
    pub dept: String,
    pub name: String,
    pub status: String,
    // pub terms_since_declaration: Option<u32>,
}

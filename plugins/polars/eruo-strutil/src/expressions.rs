#![allow(clippy::unused_unit)]
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;
use rand::Rng;
use serde::Deserialize;
use std::fmt::Write;

fn is_vowel(c: char) -> bool {
    matches!(c.to_ascii_lowercase(), 'a' | 'e' | 'i' | 'o' | 'u')
}

fn pig_latin_word(word: &str) -> String {
    if word.is_empty() {
        return String::new();
    }

    // Handle punctuation
    let (word_content, punctuation) =
    if let Some(last_char) = word.chars().last() {
        if last_char.is_ascii_punctuation() {
            (&word[0..word.len() - 1], Some(last_char))
        } else {
            (word, None)
        }
    } else {
        (word, None)
    };

    // Find the end of the initial consonant cluster
    let mut consonant_cluster_end = 0;
    if !is_vowel(word_content.chars().next().unwrap()) {
        for (i, c) in word_content.chars().enumerate() {
            if is_vowel(c) {
                consonant_cluster_end = i;
                break;
            }
            // If the word has no vowels, treat it as a special case
            if i == word_content.len() - 1 {
                consonant_cluster_end = word_content.len();
            }
        }
    }

    let result =
    if consonant_cluster_end == 0 {
        // Vowel starts the word, so just add "way"
        format!("{}way", word_content)
    } else {
        // Consonant cluster is moved to the end with "ay"
        let (consonant_cluster, rest_of_word) = word_content.split_at(consonant_cluster_end);

        let mut pig_latin_word_content = format!("{}{}{}", rest_of_word, consonant_cluster, "ay");

        // Handle capitalization
        if word_content.chars().next().unwrap().is_ascii_uppercase() {
            let first_char = pig_latin_word_content.chars().next().unwrap().to_ascii_uppercase();
            pig_latin_word_content.replace_range(..1, &first_char.to_string());
        }

        pig_latin_word_content
    };

    // Add back punctuation if it existed
    if let Some(punc) = punctuation {
        format!("{}{}", result, punc)
    } else {
        result
    }
}

#[polars_expr(output_type=String)]
fn pig_latinnify(inputs: &[Series]) -> PolarsResult<Series> {
    let ca: &StringChunked = inputs[0].str()?;
    let out: StringChunked = ca.apply_into_string_amortized(|value: &str, output: &mut String| {
        let translated_words: Vec<String> = value
            .split_whitespace()
            .map(|word| pig_latin_word(word))
            .collect();
        write!(output, "{}", translated_words.join(" ")).unwrap();
    });
    Ok(out.into_series())
}

#[derive(Deserialize)]
pub struct SplitByCharsKwargs {
    characters: String,
}

#[polars_expr(output_type=String)]
fn split_by_chars(inputs: &[Series], kwargs: SplitByCharsKwargs) -> PolarsResult<Series> {
    let ca: &StringChunked = inputs[0].str()?;
    let SplitByCharsKwargs { characters } = kwargs;
    let mut all_results: Vec<String> = Vec::new();
    for value in ca.iter() {
        if let Some(s) = value {
            for part in s.split(|c: char| characters.contains(c)) {
                all_results.push(part.trim().to_string());
            }
        }
    }
    let out: StringChunked = all_results.iter().map(|s| Some(s.as_str())).collect::<StringChunked>();
    Ok(out.into_series())
}

#[polars_expr(output_type=String)]
fn to_sentence_case(inputs: &[Series]) -> PolarsResult<Series> {
    let ca: &StringChunked = inputs[0].str()?;
    let out: StringChunked = ca.apply_into_string_amortized(|value: &str, output: &mut String| {
        // Tracks whether the next alphabetic character should be capitalized.
        let mut should_capitalize = true;

        // Looks ahead for spaces after a punctuation mark.
        let mut chars = value.chars().peekable();

        while let Some(c) = chars.next() {
            // Capitalize the current non-whitespace character.
            if should_capitalize && c.is_alphabetic() {
                output.extend(c.to_uppercase());
                should_capitalize = false;
            } else {
                output.push(c);
            }

            // Check if we just encountered a punctuation mark.
            if ".!?".contains(c) {
                // Peek at the next character to see if it's a space.
                if let Some(&next_char) = chars.peek() {
                    if next_char.is_whitespace() {
                        // If it's a space, consume all following whitespace characters.
                        while let Some(&next_c) = chars.peek() {
                            if next_c.is_whitespace() {
                                output.push(next_c);
                                chars.next(); // Consume the space
                            } else {
                                break;
                            }
                        }
                        // Capitalize the next non-whitespace character.
                        should_capitalize = true;
                    }
                }
            }
        }
    });
    Ok(out.into_series())
}

#[polars_expr(output_type=String)]
fn to_sponge_case(inputs: &[Series]) -> PolarsResult<Series> {
    let ca: &StringChunked = inputs[0].str()?;
    let mut rng = rand::rng();
    let out: StringChunked = ca.apply_into_string_amortized(|value: &str, output: &mut String| {
        for c in value.chars() {
            if c.is_alphabetic() {
                if rng.random_bool(0.5) {
                    output.extend(c.to_uppercase());
                } else {
                    output.extend(c.to_lowercase());
                }
            } else {
                output.push(c);
            }
        }
    });
    Ok(out.into_series())
}
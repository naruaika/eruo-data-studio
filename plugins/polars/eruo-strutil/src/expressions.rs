#![allow(clippy::unused_unit)]
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;
use rand::Rng;
use std::fmt::Write;

#[polars_expr(output_type=String)]
fn pig_latinnify(inputs: &[Series]) -> PolarsResult<Series> {
    let ca: &StringChunked = inputs[0].str()?;
    let out: StringChunked = ca.apply_into_string_amortized(|value: &str, output: &mut String| {
        if let Some(first_char) = value.chars().next() {
            write!(output, "{}{}ay", &value[1..], first_char).unwrap()
        }
    });
    Ok(out.into_series())
}

#[polars_expr(output_type=String)]
fn to_sentence_case(inputs: &[Series]) -> PolarsResult<Series> {
    let ca: &StringChunked = inputs[0].str()?;
    let out: StringChunked = ca.apply_into_string_amortized(|value: &str, output: &mut String| {
        // Tracks whether the next alphabetic character should be capitalized.
        let mut should_capitalize = true;

        // Looks ahead for spaces after a period.
        let mut chars = value.chars().peekable();

        while let Some(c) = chars.next() {
            // Capitalize the current non-whitespace character.
            if should_capitalize && c.is_alphabetic() {
                output.extend(c.to_uppercase());
                should_capitalize = false;
            } else {
                output.push(c);
            }

            // Check if we just encountered a period.
            if c == '.' || c == '!' || c == '?' {
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
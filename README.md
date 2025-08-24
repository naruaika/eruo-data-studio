# Eruo Data Studio

A powerful, intuitive, and integrated data platform for data analysts.

<span style="display: block; margin: -20px; margin-bottom: -10px;">
  <img src="docs/screenshot.png" alt="Eruo Data Studio" />
</span>

**Eruo Data Studio** is an innovative, free, and open-source application designed to revolutionize how you interact with and understand your data. Built on the one of the most popular data processing libraries, **Eruo Data Studio** brings together the best of Excel's flexibility, business intelligence's interactive visualization, and ETL's robust data preparation, *all in one seamless environment*.

<span style="display: block; margin: -20px; margin-bottom: -10px;">
  <img src="docs/screenshot-1.png" alt="Eruo Data Studio" />
</span>


**Disclaimer:** We know this project sounds ambitious! We're actively exploring the best path forward, balancing community needs with what's technically achievable. Our direction and approaches may evolve as we learn and build.

## Status

Currently in early development. Follow our repository for real-time updates and get ready to transform your data workflow!

## Use Cases

**Eruo Data Studio** is ideal for anyone who:

- Regularly works with datasets exceeding Excel's capacity.
- Frequently switches between Excel and BI tools for data preparation and visualization.
- Needs to perform ad-hoc analysis and complex calculations on large datasets.
- Wants to build reproducible and auditable data transformation pipelines without extensive coding.
- Seeks a single, integrated environment for data cleaning, analysis, and interactive reporting.
- Is frustrated by the limitations of current tools in handling "dirty" data or requiring specialized coding for simple tasks.

## Backgrounds

**Disclaimer:** This section specifically was written with the help of a generative AI. Its purpose is to clearly communicate the challenges we're addressing, our product vision, and the foundational ideas behind our solution.

Data professionals today constantly juggle multiple tools, leading to fragmented workflows, wasted time, and missed insights:

- **Microsoft Excel:** Unmatched for its flexibility, ad-hoc analysis, and formula-driven data manipulation. However, it struggles with large datasets (typically over 1 million rows), lacks robust data governance, and its charting capabilities are limited for interactive dashboards. Chained formulas can also become unwieldy and hard to troubleshoot.

- **Tableau/Power BI:** Excellent for handling medium to large datasets, creating interactive dashboards, and sharing insights. Yet, they often lack the granular control and immediate feedback loop for ad-hoc data cleaning or complex calculations that Excel provides. Trivial tasks like calculating days between dates or making quick adjustments to partial data can become cumbersome, requiring knowledge of specialized languages like DAX or M.

- **Alteryx Designer:** Essential for building robust, repeatable data pipelines and automating complex transformations. While powerful, they introduce another separate application, increasing context switching and a steeper learning curve for users less familiar with visual programming or scripting.

The result? Data analysts frequently switch back and forth between applications, often needing to revert to Excel mid-presentation for ad-hoc requests. This constant context switching isn't just inefficient; it breaks the analytical flow and hinders productivity.

**Eruo Data Studio** addresses these challenges head-on by providing a unified platform that combines the strengths of these disparate tools. Our core advantages include:

- **Seamless Workflow:** Prepare, analyze, visualize, and explore your data all within a single application. Eliminate the time and cognitive load of context switching, leading to faster iterations and more dynamic insights.

- **Excel-like Flexibility on Big Data:** Leverage the power of familiar formulas and cell-based manipulation, but scaled to handle millions or even billions of rows with the performance of Polars. Perform ad-hoc calculations, clean dirty data, and make quick adjustments directly within your large datasets.

- **Intuitive Data Preparation:** Define and manage complex data pipelines with ease using an intuitive, node-based graph editor, inspired by tools like Alteryx. This visual approach ensures transparency, reproducibility, and simplifies data transformation for users of all skill levels.

- **Custom Logic Integration:** Seamlessly embed custom SQL queries or Python scripts directly into your data pipelines for advanced transformations, statistical modeling, or machine learning tasks, bridging the gap between analysts and data scientists.

- **Interactive BI Visualizations:** Generate compelling, interactive dashboards and reports without ever leaving the environment where your data was prepared and analyzed.

- **Reduced Learning Curve:** While comprehensive, the integrated design means you learn one powerful tool rather than mastering multiple, distinct applications.

- **Enhanced Productivity & Collaboration:** Faster analytical cycles, combined with clear data pipelines, foster better collaboration and more consistent insights across teams.

**Eruo Data Studio** is not just about minimizing app switches; it's about reimagining the entire data analysis workflow to be more intuitive, efficient, and powerful for everyone.

## Roadmap

**Disclaimer:** Please note that this roadmap represents a highly ambitious long-term vision, potentially extending 5-10 years into the future from our current stage. Our progress will evolve with time, resources, and community engagement.

- **v0.1 — Core Data Engine & Basic Spreadsheet View:**

    - Integration with Polars for high-performance data processing.
    - Basic grid view for datasets, similar to Excel.
    - Support for simple formula application on columnar data.
    - Basic data import from CSV/Parquet.

- **v0.2 — Initial BI Visualization & Dashboarding:**

    - Drag-and-drop interface for common chart types.
    - Interactive filtering and drill-down capabilities.
    - Dashboard layout functionality.

- **v0.3 — Node-based Data Pipeline Editor:**

    - Visual graph editor for ETL steps (e.g., merge, filter, aggregate, pivot).
    - Support for custom SQL nodes.
    - Basic data export options.

- **v0.4 — Advanced Features & Extensibility:**

    - Integration of custom Python scripts within pipelines.
    - Broader data source connectivity (databases, APIs, cloud storage).
    - Improved performance optimizations for very large datasets.
    - Collaboration features (e.g., sharing reports/pipelines).

## Designing

The following are some of the resources that have informed our decision-making and development planning, highlighting common challenges and insights within the data analysis community:

- [Where does most of your data time actually go?](https://www.reddit.com/r/dataanalysis/comments/1mnfoj6/where_does_most_of_your_data_time_actually_go/)
- [Heated debate with leadership because of Excel ](https://www.reddit.com/r/datascience/comments/16tujyf/heated_debate_with_leadership_because_of_excel/)
- [What is Tableau's purpose?](https://www.reddit.com/r/tableau/comments/1lsyb4u/what_is_tableaus_purpose/)
- [Do you guys find that a lot of senior execs really dislike Tableau dashboard visualizations for reporting and monitoring?](https://www.reddit.com/r/tableau/comments/ew8jyd/do_you_guys_find_that_a_lot_of_senior_execs/)

We've also conducted research on similar applications to understand their strengths and limitations:

- [Microsoft Excel](https://www.microsoft.com/en-us/microsoft-365/excel)
- [Google Sheets](https://workspace.google.com/intl/en_id/products/sheets/)
- [Power BI](https://www.microsoft.com/en-us/power-platform/products/power-bi)
- [Tableau](https://www.tableau.com/products/desktop)
- [Alteryx Designer](https://www.alteryx.com/products/alteryx-designer)
- [SmoothCSV](https://smoothcsv.com/)

In reality, we've done research on more resources and applications, but the above are the ones that have been the most influential.

## Limitations

Currently we only support x86_64 architectures and Linux distributions using `glibc` (GNU C Library) due to lack of dependecy management by the team. Building the dependencies from the source doesn't seem to be so complicated though, so we'll make sure to try again in the near future.

Since we started developing the proof-of-concept with Libadwaita, a building blocks for GNOME applications, so it's supposed to be compatible only with GNOME desktop environment. I think it's possible that the application will still look correct and good on other distributions. Anyway, we'll add support for Windows in the future and hopefully for macOS as well as web platforms!

## Build and Run

The recommended way to build and run this project is using [GNOME Builder](https://apps.gnome.org/Builder/). Select the `com.macipra.eruo.json` manifest file and click the `Run` button.

## Development

I personally use [Visual Studio Code](https://code.visualstudio.com/), but you can use whatever your favorite is. To run and build using Flatpak on VS Code, consider installing [Flatpak](https://marketplace.visualstudio.com/items?itemName=bilelmoussaoui.flatpak-vscode) extension.

Execute the following commands in the terminal to install the dependencies (on Fedora):

```sh
sudo dnf install flatpak flatpak-builder --assumeyes
```

Select the `com.macipra.eruo.Devel.json` manifest file by typing in the command palette and running `Flatpak: Select or Change Active Manifest` (<kbd>F1</kbd> or <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd>).

Create the `run.sh` file in the `build-aux/` directory:

```sh
cp build-aux/run.sh.example build-aux/run.sh
```

To build the plugins, we need the `rustup` and `maturin` installed:

```sh
sudo dnf install rustup maturin --assumeyes
rustup-init
```

Note that despite we call it "plugins", they're actually mandatory dependencies by now. Building all plugins is simply a matter of running the following command:

```sh
chmod +x build-aux/build.sh
./build-aux/build.sh
```

Finally, type in the command palette and run `Flatpak: Build and Run` or simply hit <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>B</kbd>.

To override some environment variables or to add command-line arguments to the application, you can update the `build-aux/run.sh` file, for example:

```txt
#!/bin/bash
GTK_DEBUG= EDS_DEBUG= /app/bin/eruo-data-studio "~/Datasets/Anime Quotes/AnimeQuotes_case.csv" "$@"
```

If you're using a Python language server, you may want to install the requirements. For better dependency management, it's recommended to create a virtual environment rather than installing packages globally:

```sh
python -m venv .pyenv
source .pyenv/bin/activate
pip install -r requirements-devel.txt
```

To add new dependencies using [`pip`](https://packaging.python.org/en/latest/key_projects/#pip) to the [`flatpak-builder`](https://docs.flatpak.org/en/latest/flatpak-builder.html) manifest json file, you can use the [`flatpak-pip-generator`](https://github.com/flatpak/flatpak-builder-tools/tree/master/pip). Either adding the reference to the `com.macipra.eruo*.json` files or copy-pasting the content directly into the manifest files and delete the generated file. Do not forget to update the `requirements*.txt` files as well.

When it comes to the plugin development, usually I do this following example steps:

1. Activate the virtual environment: `source .pyenv/bin/activate`

1. Go to the plugin directory: `cd plugins/polars/eruo-strutil`

1. Check if there's any dependency issues: `cargo check`

1. Install the plugin in the current virtual environment: `maturin develop`

1. Write/update some tests in `test/` directory

1. Run the tests, make sure they all pass: `pytest -vv -s`

1. Build the plugin as a wheel (.whl) file: `maturin build --release`

1. Copy the wheel file to the `dist` directory: `cp target/wheels/*.whl ../../../dist/`

1. Type in the command palette and run:

    1. `Run Flatpak: Update Dependencies`
    1. `Run Flatpak: Build and Run` (or <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>B</kbd>)

1. Update the related files if necessary. For example, if we want to bump the version up, we need to update `Cargo.toml` and the related files in the `build-aux/` directory. We need to publish it to the [PyPI](https://pypi.org/) if it's a Python package.

## Licenses

This project is distributed under the [MIT License](LICENSE). We use GTK and [Libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) to build the user interface, which are licensed under the [GNU Lesser General Public License Version 2.1](https://www.gnu.org/licenses/lgpl-2.1.en.html). The backend for data manipulation uses [Polars](https://pola.rs/) and [DuckDB](https://duckdb.org/), which are distributed under the [MIT License](https://opensource.org/license/mit). For other dependencies, see the `requirements.txt` file. We use icons from [Carbon Design System](https://carbondesignsystem.com/elements/icons/library/), which is distributed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
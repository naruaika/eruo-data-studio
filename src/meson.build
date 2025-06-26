pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'eruo_data_studio'
gnome = import('gnome')

gnome.compile_resources('eruo-data-studio',
  'eruo-data-studio.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'eruo-data-studio.in',
  output: 'eruo-data-studio',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

eruo_data_studio_sources = [
  '__init__.py',
  'utils.py',

  'dbms.py',
  'display.py',
  'renderer.py',
  'selection.py',

  'main.py',
  'window.py',
]

install_data(eruo_data_studio_sources, install_dir: moduledir)

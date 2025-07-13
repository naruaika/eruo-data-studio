desktop_file = i18n.merge_file(
        input: 'com.macipra.eruo.desktop.in',
       output: 'com.macipra.eruo.desktop',
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
        input: 'com.macipra.eruo.metainfo.xml.in',
       output: 'com.macipra.eruo.metainfo.xml',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])

install_data('com.macipra.eruo.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

gnome = import('gnome')

pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'eruo_data_studio'

gnome.compile_resources('eruo-data-studio',
  'eruo-data-studio.gresource.xml',
  gresource_bundle: true,
  source_dir: '../src',
  install: true,
  install_dir: pkgdatadir,
)

compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])

service_conf = configuration_data()
service_conf.set('bindir', get_option('prefix') / get_option('bindir'))
configure_file(
  input: 'com.macipra.eruo.service.in',
  output: 'com.macipra.eruo.service',
  configuration: service_conf,
  install_dir: get_option('datadir') / 'dbus-1' / 'services'
)

subdir('icons')

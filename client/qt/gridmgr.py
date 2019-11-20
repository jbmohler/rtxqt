import inspect
import urllib.parse
from PySide2 import QtCore, QtWidgets
import rtlib
import apputils
import apputils.models as models
import apputils.viewmenus as viewmenus

RTX_EXTENSION_PLUGS = []

def add_extension_plug(plug):
    global RTX_EXTENSION_PLUGS
    RTX_EXTENSION_PLUGS.append(plug)

def search_export(sbname, state, exports_dir):
    state = QtWidgets.QApplication.instance()

    global RTX_EXTENSION_PLUGS
    for plug in RTX_EXTENSION_PLUGS:
        f = getattr(plug, 'report_formats', None)
        if f != None:
            sb = f(state, sbname)
        else:
            sb = None
        if sb != None:
            return sb

def search_sidebar(sbname, state, exports_dir):
    state = QtWidgets.QApplication.instance()

    global RTX_EXTENSION_PLUGS
    for plug in RTX_EXTENSION_PLUGS:
        f = getattr(plug, 'load_sidebar', None)
        if f != None:
            sb = f(state, sbname)
        else:
            sb = None
        if sb != None:
            return sb

def get_menus():
    global RTX_EXTENSION_PLUGS
    for plug in RTX_EXTENSION_PLUGS:
        f = getattr(plug, 'get_menus', None)
        for menuname, items in f():
            yield (menuname, items)

def url_params(url):
    values = dict(url.queryItems())
    # TODO figure out correct +-decoding
    values = {k: v.replace('+', ' ') for k, v in values.items()}
    values = {k: urllib.parse.unquote(v) for k, v in values.items()}
    return values

def show_link_parented(parent, url):
    if not isinstance(url, QtCore.QUrl):
        url = QtCore.QUrl(url)

    # prepare API on url for plugs
    url.parameters = lambda url=url: url_params(url)
    state = QtWidgets.QApplication.instance()

    global RTX_EXTENSION_PLUGS
    handled = False
    for plug in RTX_EXTENSION_PLUGS:
        if plug.show_link_parented(state, parent, url):
            handled = True
            break

    if not handled:
        apputils.information(parent, 'Invalid URL string:  {}'.format(url))

def show_link(url):
    from . import winlist
    show_link_parented(winlist.main_window(), url)

def url_handler(col, ctxmenu):
    def view_item():
        row = ctxmenu.active_index.data(models.ObjectRole)
        show_link(QtCore.QUrl(rtlib.column_url(col, row)))

    return view_item

ObjectRole = models.ObjectRole
UrlRole = models.UrlRole

def callable_handler(col, ctxmenu, callback, reloads):
    def make_callback():
        row = ctxmenu.active_index.data(models.ObjectRole)
        args = rtlib.column_url_args(col, row)
        result = callback(ctxmenu.parent(), *args)
        if reloads and result != False:
            ctxmenu.triggerReload.emit(row)

    return make_callback

def callable_should_appear(index, column):
    row = index.data(models.ObjectRole)
    if hasattr(row.__class__, 'model_columns'):
        return column.attr in row.__class__.model_columns
    return True

def callable_is_enabled(index, column):
    row = index.data(models.ObjectRole)
    if hasattr(row.__class__, 'model_columns'):
        thecol = row.__class__.model_columns.get(column.attr)
    else:
        thecol = column
    if thecol == None:
        return False
    if thecol.url_key == None:
        checkattr = thecol.attr
    else:
        checkattr = thecol.url_key.split(',')[0]
    return getattr(row, checkattr, None) != None

def apply_column_url_views(ctxmenu, model, no_default=False):
    for col in model.columns:
        for action_defn in col.actions:
            if action_defn.matches_scope(col):
                action = None
                if action_defn.callback == '__url__':
                    if col.url_factory != None:
                        action = QtWidgets.QAction(ctxmenu.parent())
                        action.triggered.connect(url_handler(col, ctxmenu))
                        action.should_appear = lambda index, column=col: callable_should_appear(index, column)
                        action.is_enabled = lambda index, column=col: callable_is_enabled(index, column)
                else:
                    action = QtWidgets.QAction(ctxmenu.parent())
                    action.triggered.connect(callable_handler(col, ctxmenu, action_defn.callback, action_defn.reloads))

                if action != None:
                    label = action_defn.interpolated_label(col)
                    action.setText(label)
                    isdefault = col.represents and action_defn.defaulted and not no_default
                    ctxmenu.add_action(action, default=isdefault)

class ReportClientRowRelateds:
    def __init__(self, *args):
        # read in & interpret anything the server sends in a client-row-relateds

        assert len(args) == 4
        assert type(args[0]) is str
        assert type(args[1]) is str
        assert type(args[2]) is dict
        assert type(args[3]) is dict

        self.label = args[0]
        self.url_base = args[1]
        self.url_static_params = args[2]
        self.url_dyn_params = args[3]

    def action(self, parent, ctxmenu):
        act = QtWidgets.QAction(self.label, parent)
        act.triggered.connect(lambda cx=ctxmenu: self.act_on(ctxmenu))
        return act

    def act_on(self, ctxmenu):
        row = ctxmenu.active_index.data(models.ObjectRole)
        params = self.url_static_params.copy()
        dynparams = {k: getattr(row, v) for k, v in self.url_dyn_params.items()}
        params.update(dynparams)
        p2 = urllib.parse.urlencode(params)
        url = '{}?{}'.format(self.url_base, p2)
        show_link(url)

def apply_client_row_relateds(ctxmenu, content):
    rel = content.keys.get('client-row-relateds', [])
    ctxmenu.rcrr = [ReportClientRowRelateds(*x) for x in rel]
    for rc in ctxmenu.rcrr:
        ctxmenu.add_action(rc.action(ctxmenu.parent(), ctxmenu))

def apply_client_relateds(ctxmenu, content):
    relateds = content.keys.get('client-relateds', [])
    actions = []
    for label, link in relateds:
        act = QtWidgets.QAction(label, ctxmenu.parent())
        def action(xlink=link):
            show_link(xlink)
        act.triggered.connect(lambda: action())
        actions.append(act)
        ctxmenu.addAction(act)
    return actions


def client_table_as_model(table, parent, include_data=True, blank_row=False):
    m = models.ObjectQtModel(table.columns, parent=parent)
    if include_data:
        if blank_row:
            xx = table.DataRow(*tuple((None,)*len(table.DataRow.__slots__)))
            m.set_rows([xx] + table.rows)
        else:
            m.set_rows(table.rows)
    return m

class GridManager(QtCore.QObject):
    current_row_update = QtCore.Signal()

    def __init__(self, grid, parent, fixed_rowset=False):
        QtCore.QObject.__init__(self, parent)

        self.grid = grid
        self.table = None

        self._core_actions = []
        self.fixed_rowset = True

        self.ctxmenu = viewmenus.ContextMenu(self.grid, parent)
        self.ctxmenu.contextActionsUpdate.connect(self.context_actions_update)
        self.ctxmenu.current_row_update.connect(self.context_actions_update)
        self.ctxmenu.current_row_update.connect(self.current_row_update.emit)

    def add_action(self, act, is_active=None, triggered=None):
        if isinstance(act, str):
            act = QtWidgets.QAction(act, self.grid)
        act.is_active = is_active
        self._core_actions.append(act)

        act.triggered.connect(lambda: self.call_core_func(triggered))

    def context_actions_update(self):
        for act in self._core_actions:
            if act.is_active != None:
                act.setEnabled(self.call_core_func(act.is_active))

    def selected_row(self):
        x = self.ctxmenu.active_index
        return x.data(models.ObjectRole) if x != None else None

    def selected_rows(self):
        rowmap = {}
        for index in self.ctxmenu.selected_indexes():
            rowmap[index.row()] = index.data(models.ObjectRole)
        return [obj for _, obj in sorted(rowmap.items(), key=lambda x: x[0])]

    def call_core_func(self, f):
        args = inspect.getargspec(f).args
        kwargs = {}
        for a in args:
            v = None
            if a == 'rows':
                v = self.selected_rows()
            elif a == 'row':
                if self.ctxmenu.active_index != None:
                    v = self.ctxmenu.active_index.data(models.ObjectRole)
                else:
                    v = None
            else:
                continue
            kwargs[a] = v
        return f(**kwargs)

    def _post_model_action(self):
        self.ctxmenu.update_model()
        self.ctxmenu.reset_action_list()
        # add column dynamic items
        apply_column_url_views(self.ctxmenu, self.grid.model())
        # add client-row-relateds
        # TODO: support this
        # apply_client_row_relateds(self.ctxmenu, self.run.content)
        #self.my_actions = apply_client_relateds(self.power_menu, self.run.content)
        if not self.fixed_rowset:
            self.ctxmenu.add_action(self.delete_action)
        for act in self._core_actions:
            self.ctxmenu.add_action(act)

    def set_client_table(self, table):
        self.table = table
        m = client_table_as_model(self.table, self.parent(), include_data=False)
        self.grid.setModel(m)

        rset = list(self.table.rows)
        f = None
        if not self.fixed_rowset:
            f = self.table.flipper_row()
        m.set_rows(rset, flipper=f)

        self._post_model_action()

    def set_client_table_no_model(self, table):
        self.table = table
        m = self.grid.model()

        rset = list(self.table.rows)
        f = None
        if not self.fixed_rowset:
            f = self.table.flipper_row()
        m.set_rows(rset, flipper=f)

        self._post_model_action()

class ThunkImporter:
    def __init__(self, import_row=None, assess_row=None):
        self.import_row = import_row
        self.assess_row = assess_row

class EditableGridManager(GridManager):
    def __init__(self, grid, parent, fixed_rowset=False):
        QtCore.QObject.__init__(self, parent)

        self.grid = grid
        self.table = None

        self._core_actions = []
        self.fixed_rowset = fixed_rowset

        self.delete_action = QtWidgets.QAction('&Delete Row', self.grid)
        self.delete_action.setShortcut('Ctrl+Delete')
        self.delete_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.delete_action.triggered.connect(self.delete_current_row)

        if not self.fixed_rowset:
            self.grid.addAction(self.delete_action)

        self.ctxmenu = viewmenus.ContextMenu(self.grid, parent)
        self.ctxmenu.contextActionsUpdate.connect(self.context_actions_update)

    @property
    def importer(self):
        return self.ctxmenu.importer

    @importer.setter
    def importer(self, v):
        self.ctxmenu.importer = v

    def delete_current_row(self):
        if not self.table:
            return 

        # get selection from grid & delete
        index = self.grid.currentIndex()
        row = index.data(models.ObjectRole)

        self.table.recorded_delete(row)
        m = self.grid.model()
        m.removeRow(index.row(), index.parent())

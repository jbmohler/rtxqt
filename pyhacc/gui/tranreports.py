import re
import itertools
import rtlib.server as rtserve

def group_footer_profit(wbhelper, worksheet, bounding_box, footer_index):
    i1 = bounding_box.row_index_start
    i2 = bounding_box.row_index_end
    for col in bounding_box.columns:
        if None != re.match('^(debit|credit|balance)(_|)[0-9]*$', col.attr):
            formula = '=SUM({}:{})'.format(col.cell(i1), col.cell(i2))
            total = sum([getattr(row, col.attr) for row in bounding_box.rows if getattr(row, col.attr) != None])
            worksheet.write_formula(footer_index, col.index, formula, wbhelper.bold_currency_format, value=total)
        elif col.attr == 'acc_name':
            worksheet.write(footer_index, col.index, 'Total', wbhelper.bold_format)
    return 2

class AccountTypeGrouped:
    TITLE = 'Type Summarized Excel'

    def export(self, fname, v, content):
        rtserve.export_view(fname, v, 
                    headers=content.keys['headers'],
                    options={'row_group': 'atype_name'}, 
                    sort_key='(atype_sort, jrn_name, acc_name)',
                    group_end_callback=group_footer_profit)

def full_summary(wbhelper, worksheet, bounding_box, footer_index):
    i1 = bounding_box.row_index_start
    i2 = bounding_box.row_index_end
    for col in bounding_box.columns:
        if None != re.match('^(debit|credit|balance|amount)(_|)[0-9]*$', col.attr):
            formula = '=SUM({}:{})'.format(col.cell(i1), col.cell(i2))
            total = sum([getattr(row, col.attr) for row in bounding_box.rows if getattr(row, col.attr) != None])
            worksheet.write_formula(footer_index, col.index, formula, wbhelper.bold_currency_format, value=total)
        elif col.attr == 'payeee':
            worksheet.write(footer_index, col.index, 'Total', wbhelper.bold_format)
    return 2

class FullGrouped:
    TITLE = 'Summarized Excel'

    def export(self, fname, v, content):
        model = v.model()
        model.rows.sort(key=lambda x: x.payee)
        sums = []
        nz = lambda v: v if v != None else 0.
        for key, xx in itertools.groupby(model.rows, lambda x: x.payee):
            sums.append((key, sum([nz(x.debit)-nz(x.credit) for x in xx])))
        sums.sort(key=lambda x: -x[1])
        assign = {}
        for index, tu in enumerate(sums):
            assign[tu[0]] = index
        for row in model.rows:
            row.sort_index = assign[row.payee]

        rtserve.export_view(fname, v, 
                    headers=content.keys['headers'],
                    options={'row_group': 'payee'}, 
                    sort_key='(sort_index, payee, date)',
                    group_end_callback=full_summary)

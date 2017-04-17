import re
import os
import pandas as pd
from numpy import array, isfinite

import plotly.plotly as py
import plotly.tools as tools
import plotly.graph_objs as go


USER_NAME = os.environ['PLOTLY_USER_NAME']
API_KEY = os.environ['PLOTLY_API_KEY']
py.sign_in(username=USER_NAME, api_key=API_KEY)

# This is a function that will process the incoming files and provide the graphs and information
# that is required for the dashboard

def dashboard(roofs, worders, projects, receivables, start_date='2016-01-01'):
    # type: (file, file, file, file, file) -> dictionary
    # Dashboard reads 4 CSV files and given a start_date and end_date
    # Returns in a dictionary:
    # 0)  The URL of the first plot: first_plot_url
    # 1)  A string containing the number of calls and percentage handled by warranty
    # 2)  The number of billed calls
    # 3)  The average price per call
    # 4)  The number of repairs
    # 5)  The average price of repairs
    # 6)  The average cost per project
    # 7)  The average spread per project
    # 8)  The number of projects completed
    # 9)  A savings text
    # 10) The URL of the second plot: second_plot_url
    # 11) The average cost per inspection

    # First we read in the 4 files that we are going to need to make the report

    '''
    :param start_date: string or datetime of when dashboard starts
    :param roofs: csv file containing roof condition info
    :param worders: csv file containing work order report
    :param projects: csv file containing project information
    :param receivables: csv file containing receivables info
    '''

    roofs = pd.read_csv(roofs)
    worders = pd.read_csv(worders)
    projects = pd.read_csv(projects)
    receivables = pd.read_csv(receivables)

    # We process the files to remove some commas from numbers

    receivables["INVOICE AMOUNT"] = receivables["INVOICE AMOUNT"].map(lambda x: x.replace(",", ""))
    projects[["BID AMOUNT"]] = projects[["BID AMOUNT"]].replace('[\$,]', '', regex=True).astype("float64")
    projects["YEAR"] = pd.to_datetime(projects["STATUSDATE"]).dt.year
    projects["STATUSDATE"] = pd.to_datetime(projects["STATUSDATE"])

    dashboard_values = [pie_chart_url(roofs)]

    dashboard_values = dashboard_values + upper_right_stats(worders, receivables, projects, start_date)

    dashboard_values = dashboard_values + [second_graph_url(projects, start_date)] +\
                       [avg_cost_inspection(receivables)]

    #dashboard_values.update(upper_right_stats(worders, receivables, projects, start_date))

    return dashboard_values


def count_conditions(roofs):
    '''
    :param roofs: a pandas dataframe of roof conditions
    :return: a tuple containing a list of labels and a list of values
    '''

    # Part 1: Creating the pie chart

    ### We will read the data from the roof inspections and count
    ### each of the different types of roof conditions that exists

    # First let's filter roofs whose condition are NaN

    roofs = roofs[pd.notnull(roofs["Roof Condition"])]
    conditions = roofs['Roof Condition']

    labels = ["Excellent", "Good", "Fair", "Poor", "Bad"]
    values = [sum(conditions == label) for label in labels]
    return labels, values


def pie_chart_url(roofs):
    '''
    :param roofs: a csv file with roof information
    :return: a url for a plotly pie chart
    '''

    labels, values = count_conditions(roofs)

    fig = {
        'data': [{'labels': labels,
                  'values': values,
                  'textinfo': 'label+value+percent',
                  'textposition': 'inside+outside',
                  'pull': 0.1,
                  'rotation': 70,
                  'showlegend': False,
                  'sort': False,
                  'type': 'pie'}],
        'layout': {'title': '<b>Inspections</b><br><i>Total Completed {}</i>'.format(sum(values))}
    }

    fig['layout'].update(paper_bgcolor='rgb(248, 248, 255)',
                         plot_bgcolor='rgb(248, 248, 255)')

    return py.plot(fig, filename='BPW Pie Chart', auto_open=False, )


def avg_cost_inspection(receivables):
    '''
    :param receivables: a pandas dataframe of receivables
    :return: the average cost of the inspection receivable
    '''

    inspections = receivables[receivables["WORKORDER TYPE"] == "Inspection"]

    return "Average cost for each inspection: ${:,.2f}".format(
        inspections["INVOICE AMOUNT"].astype("float64").mean())


def upper_right_stats(worders, receivables, projects, start_date):
    '''
    :rtype: dict
    :param worders: a pandas frame of work orders
    :param receivables: a pandas frame of receivables
    :param start_date: start date of the report
    :return: a dictionary with
        # 2)  A string containing the number of calls and percentage handled by warranty
        # 3)  The number of billed calls
        # 4)  The average price per call
        # 5)  The number of repairs
        # 6)  The average price of repairs
        # 7)  The average cost per project
        # 8)  The average spread per project
        # 9)  The number of projects completed
        # 10) A savings text
    '''

    # Part 2: Upper Right Hand Corner of Report

    worders = worders[pd.notnull(worders["SUBTYPE"])]
    worders = worders[worders["STATUS"] == "COMPLETED"]
    leaks = pd.concat(
        [worders[worders["SUBTYPE"] == "Leak Call "], worders[worders["SUBTYPE"] == "Leak Call - Emergency"]])

    # Number of calls handled by warranty
    warranty = sum(leaks['FINANCIAL_RESPONSIBILITY'] == 'INTERNAL CHARGE')
    warranty += sum(worders["SUBTYPE"] == "Warranty - Leak Call")

    # Average price per call
    billed_calls = pd.concat([receivables[receivables["WORKORDER SUBTYPE"] == "Leak Call "],
                              receivables[receivables["WORKORDER SUBTYPE"] == "Leak Call - Emergency"]])
    avg_price_call = billed_calls["INVOICE AMOUNT"].astype("float64").mean()
    avg_price_call = "${:,.2f}".format(avg_price_call)

    # Number of billed calls
    num_bill_calls = billed_calls.shape[0]

    # Number of repair calls

    repairs = receivables[receivables["WORKORDER SUBTYPE"] == "Repairs "]
    num_repairs = repairs.shape[0]

    # Average price per repair job

    avg_repairs = repairs["INVOICE AMOUNT"].astype("float64").mean()
    avg_repairs = "${:,.2f}".format(avg_repairs)

    percent_warranty = " ({:,.0f}%)".format(warranty * 100 / float(num_bill_calls + warranty))

    # Now to get the spread of the projects
    # We'll have to filter the completed projects to be
    # correction to "(7) COMPLETED"
    completed = pd.concat([projects[projects["STATUS"] == "(8) COMPLETED"],
                          projects[projects["STATUS"] == "(7) COMPLETED PENDING W.D.I."]])
    mask = (completed["STATUSDATE"] > start_date) & (completed["BID AMOUNT"] > 1)
    completed = completed.loc[mask]

    # Number of Projects completed in 2016

    num_completed = completed.shape[0]


    # Now to calculate the spread

    completed["SPREAD"] = completed["BID AMOUNT"] - completed["REVISEDCONTRACTAMOUNT"]
    avg_spread = completed["SPREAD"].mean()
    avg_spread_text = "${:,.0f}".format(avg_spread)

    # Now to calculate savings
    savings = num_completed * avg_spread
    savings_text = avg_spread_text + ' = ${:,.0f} potential savings'.format(savings)

    avg_cost = completed["BID AMOUNT"].mean()
    avg_cost_text = "${:,.0f}".format(avg_cost)

    return [
            str(warranty) + percent_warranty,
            str(num_bill_calls),
            avg_price_call,
            num_repairs,
            avg_repairs,
            avg_cost_text,
            avg_spread_text,
            str(num_completed),
            savings_text
            ]


def second_graph_numbers(projects, start_date='2016-01-01'):
    '''
    :param projects:
    :param start_date:
    :return: status_labels, status_counts, total_bought, total_projects:
    '''
    # We have the number of projects completed for the above

    # 1) The Number of completed is num_completed
    projects_now = projects[projects['STATUSDATE'] >= start_date]
    # Correction to '(7) COMPLETED', '(8) ON-HOLD'
    # num_completed = sum(projects_now['STATUS'] == '(7) COMPLETED')
    num_completed = sum(projects_now['STATUS'] == '(8) COMPLETED')
    num_completed += sum(projects_now['STATUS'] == '(7) COMPLETED PENDING W.D.I.')

    # 2) Now let's calculate in-progress projects

    in_progress = projects[projects['STATUS'] == '(6) IN-PROGRESS']
    num_in_progress = in_progress.shape[0]

    # 3) Now for the number rejected

    rejected = sum(projects_now['STATUS'] == '(5) PROPOSAL REJECTED')

    # 4,5,6) Now for the number on-hold, approved, proposals pending

    on_hold = sum(projects['STATUS'] == '(9) ON-HOLD')
    approved = sum(projects['STATUS'] == '(4) APPROVED')
    proposal = sum(projects_now['STATUS'] == '(3) PROPOSAL PENDING')

    # 7,8) Preparing, Bidding

    preparing = sum(projects_now['STATUS'] == '(1)PREPARING SPECFICIATION')
    bidding = sum(projects['STATUS'] == '(2) BIDDING')

    # Now let's put the labels and the amounts in a nice lists

    status_labels = ["PREPARING", "BIDDING", "PROPOSALS<br>PENDING", "APPROVED",
                     "PROPOSALS<br>REJECTED", "IN-PROGRESS", "ON-HOLD", "COMPLETED"]
    status_counts = [preparing, bidding, proposal, approved,
                     rejected, num_in_progress, on_hold, num_completed]

    total_bought = num_completed + num_in_progress + approved
    total_projects = sum(status_counts)

    return status_labels, status_counts, total_bought, total_projects


def project_overlay_tearoff(projects, start_date='2016-01-01'):
    '''
    :param projects:
    :param start_date:
    :return:
    '''

    mask = (projects['STATUSDATE'] >= start_date) & \
           (projects['STATUS'] != "(3) PROPOSAL PENDING") & \
           (pd.notnull(projects["CONTRACT TERMS NOTES"]))

    # projects = projects[projects['STATUSDATE'] >= start_date]
    # projects = projects[projects['STATUS'] != "(3) PROPOSAL PENDING"]
    # projects = projects[pd.notnull(projects["CONTRACT TERMS NOTES"])]

    projects = projects.loc[mask]
    projects['SQFT'] = projects['CONTRACT TERMS NOTES'].map(add_sqft)
    projects = projects[projects["SQFT"] > 100]

    proj_type = projects.groupby("TYPE").sum()
    proj_type["AVGCOSTSQFT"] = proj_type["REVISEDCONTRACTAMOUNT"] / proj_type["SQFT"]

    proj_values = [round(item, 2) for item in proj_type['AVGCOSTSQFT']]
    proj_labels = [item for item in proj_type.index]

    # Now we want to separate the tear off and overlay into groups
    sqft_labels = ["0-10,000", "10,000-25,000", "25,000-50,000", "50,000 and up"]
    factor = pd.cut(projects['SQFT'], bins=[0, 10000, 25000, 50000, 9000000],
                    labels=sqft_labels)
    proj_type_sqft = projects.groupby(['TYPE', factor]).sum()
    proj_type_sqft['AVGCOSTSQFT'] = proj_type_sqft['REVISEDCONTRACTAMOUNT'] / proj_type_sqft['SQFT']

    if 'Reroof (Overlay)' in proj_type.index:
        overlay_group = proj_type_sqft.ix["Reroof (Overlay)"]
        overlay_values = [round(overlay_group.ix[label, "AVGCOSTSQFT"], 2) for label in sqft_labels]
    else:
        overlay_values = [0, 0, 0, 0]

    if 'Reroof (Tear-off)' in proj_type.index:
        tear_off_group = proj_type_sqft.ix["Reroof (Tear-off)"]
        tear_off_values = [round(tear_off_group.ix[label, "AVGCOSTSQFT"], 2) for label in sqft_labels]
    else:
        tear_off_values = [0, 0, 0, 0]

    return proj_labels, proj_values, sqft_labels, overlay_values, tear_off_values


def second_graph_url(projects, start_date='2016-01-01'):
    '''
    :param projects: pandas dataframe
    :param start_date: string of datetime
    :return: second url for graph
    '''
    status_labels, status_counts, total_bought, total_projects = second_graph_numbers(projects, start_date)

    proj_labels, proj_values, sqft_labels, overlay_values, tear_off_values = project_overlay_tearoff(projects,
                                                                                                     start_date)

    trace1 = go.Bar(
        y=status_labels,
        x=status_counts,
        name='Project',
        orientation='h'
    )

    trace2 = go.Bar(
        y=proj_values,
        x=proj_labels,
        name='Avg Cost Sqft',
        orientation='v')

    trace3 = go.Bar(
        y=sqft_labels,
        x=tear_off_values,
        name='Tear-off',
        orientation='h'
    )

    trace4 = go.Bar(
        y=sqft_labels,
        x=overlay_values,
        name='Overlay',
        orientation='h'
    )

    fig = tools.make_subplots(rows=2, cols=9,
                              specs=[
                                  [{'colspan': 3, 'rowspan': 2}, None, None, {'colspan': 3, 'rowspan': 2}, None, None,
                                   None, {'colspan': 2}, None],
                                  [None, None, None, None, None, None, None, {'colspan': 2}, None]],
                              print_grid=True,
                              subplot_titles=["<b>SNAPSHOT OF PROJECT STATUS<br>TOTAL {}</b>".format(
                                  total_projects),
                                              "<b>AVERAGE COST PER SQUARE FOOT</b>", "<b>TEAR OFF</b>",
                                              "<b>OVERLAY</b>"]
                              )

    fig.append_trace(trace1, 1, 1)
    fig.append_trace(trace2, 1, 4)
    fig.append_trace(trace3, 1, 8)
    fig.append_trace(trace4, 2, 8)

    # Adding labels to the first subplot
    annotations = []
    for x1, y1 in zip(status_labels, status_counts):
        annotations.append(dict(xref='x1', yref='y1',
                                y=x1, x=y1 + 3,
                                text=str(y1),
                                font=dict(family='Arial', size=12,
                                          color='rgb(50, 171, 96)'),
                                showarrow=False))

    for x2, y2 in zip(proj_labels, proj_values):
        annotations.append(dict(xref='x2', yref='y2',
                                y=y2 + 0.3, x=x2,
                                text="${:,.2f}".format(y2),
                                font=dict(family='Arial', size=12,
                                          color='rgb(50, 171, 96)'),
                                showarrow=False))

    tear_off_x3 = array(sqft_labels)[isfinite(tear_off_values)]
    tear_off_y3 = array(tear_off_values)[isfinite(tear_off_values)]

    for x3, y3 in zip(tear_off_x3, tear_off_y3):
        annotations.append(dict(xref='x3', yref='y3',
                                y=x3, x=y3 + 2,
                                text="${:,.2f}".format(y3),
                                font=dict(family='Arial', size=12,
                                          color='rgb(50, 171, 96)'),
                                showarrow=False))

    overlay_x4 = array(sqft_labels)[isfinite(overlay_values)]
    overlay_y4 = array(overlay_values)[isfinite(overlay_values)]

    for x4, y4 in zip(overlay_x4, overlay_y4):
        annotations.append(dict(xref='x4', yref='y4',
                                y=x4, x=y4 + 2,
                                text="${:,.2f}".format(y4),
                                font=dict(family='Arial', size=12,
                                          color='rgb(50, 171, 96)'),
                                showarrow=False))

    # Footer
    # annotations.append(dict(xref='paper', yref='paper',
    #                        x='center', y="paper",
    #                        text='AVERAGE COST PER PROJECT (2016):${:,.0f}'.format(avg_cost),
    #                        font=dict(family='Arial', size=12),
    #                        showarrow=False))

    fig['layout'].update(showlegend=False,
                         title='<b>TOTAL NUMBER OF PROJECTS DONE - {} BOUGHT</b>'.format(total_bought),
                         paper_bgcolor='rgb(248, 248, 255)',
                         plot_bgcolor='rgb(248, 248, 255)',
                         font=dict(size=10),
                         height=500,
                         width=1000,
                         titlefont=dict(size=18),
                         annotations=dict(font=dict(size=10)))

    fig['layout']['annotations'] += annotations

    return py.plot(fig, auto_open=False, filename='Project Snapshot')


def add_sqft(string):
    '''
    :param string:
    :return: a float of results
    '''
    if string == "":
        return ""
    else:
        results = re.findall(r'([^\$]\d*[,\.]?\d*[,\.]?\d+)\s*s?q?', string)
        results = [float(result.replace(",", "").replace(".", "")) for result in results]
        results = sum(results)
    return results
import os
from flask import Flask, render_template, redirect, url_for, session, flash
from flask_bootstrap import Bootstrap, bootstrap_find_resource
from flask_moment import Moment
from flask_wtf import Form
from wtforms import DateField, StringField, SubmitField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired #, Regexp
from flask_weasyprint import HTML, render_pdf, CSS

from bpw_graphs import dashboard

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

bootstrap = Bootstrap(app)
moment = Moment(app)

class UploadForm(Form):
    client = StringField('Client Name', validators = [DataRequired()])
    start = DateField('Start Date for Dashboard (mm/dd/YYYY)', validators=[DataRequired()], format= "%m/%d/%Y")
    #end = DateField('End Date for Dashboard (Optional)', validators=[Optional()], format="%m-%d-%Y")
    roofs = FileField('Roof_Condition_Export file', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV Files Only!')
    ])
    worders = FileField('Work_Order_Export file', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV Files Only!')
    ])
    projects = FileField('Custom_Project_Export file', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV Files Only!')
    ])
    receivables = FileField('Custom_Accounts_Receivable_Export file', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV Files Only!')
    ])
    submit = SubmitField('PRESS TO CREATE DASHBOARD')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    if form.validate_on_submit():
        roofs = form.roofs.data.stream
        worders = form.worders.data.stream
        projects = form.projects.data.stream
        receivables = form.receivables.data.stream
        start_date = form.start.data.strftime('%m/%d/%Y')
        try:
            dash_list = dashboard(roofs, worders, projects,receivables, start_date)
        except:
            flash('One or more of the CSV files is the wrong file')
            return redirect(url_for('index'))
        client_name = form.client.data
        form.client.data = ''
        session['client_name'] = client_name
        session['dash_list'] = dash_list
        session['start_date'] = start_date
        return redirect(url_for('dash'))
    return render_template("index.html", form = form)


@app.route('/dashboard')
def dash():
    dash_list = session.get('dash_list')
    start_date = session.get('start_date')
    client_name = session.get('client_name')
    return render_template('dashboard.html', dash_list = dash_list, start_date = start_date,
                           client_name = client_name)

@app.route('/dashboard.pdf')
def dash_pdf():
    dash_list = session.get('dash_list')
    start_date = session.get('start_date')
    client_name = session.get('client_name')
    html = render_template('dashboard_pdf.html', dash_list = dash_list, start_date = start_date,
                           client_name = client_name)
    return render_pdf(HTML(string=html),stylesheets=[
                                                     CSS(string='@page { size: A3 portrait;'
                                                                'background-color: #f8f8ff ;'
                                                                ' margin: 2cm };'
                                                                '* { float: none !important; };'
                                                                '@media print { nav { display: none; }'
                                                                '.piechart{width:200px; }')
                                                     ])

if __name__ == '__main__':
    app.run()
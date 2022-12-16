config = list()

# This is an installation specific configuration option; see app.R on how the value is obtained
# config$datapi_url = "http://localhost:5004/dbquery"

config$data_query = "
		set nocount on
		select 
			r.nivel_function,
			s.user_id, 
			s.id,
			s.group_identifier as group_id, 
			d.identifier as variable, 
			d.value, 
			s.simulient_timestamp as tstamp, 
			datepart(hh, s.simulient_timestamp) as hour, 
			datepart(mi, s.simulient_timestamp) as minute, 
			cast(t.dt as datetime) as date, t.day_of_month, t.day_of_week, t.month, t.month_label, t.week_label, t.week, t.year 
		from data.simulient_run r 
			inner join data.simulient_step s on r.id = s.run 
			inner join data.simulient_detail d on s.id = d.step 
			inner join util.dt t on cast (s.simulient_timestamp as date) = t.dt 
			inner join
				(
					select distinct s.id
					from data.simulient_step s
						inner join data.simulient_detail d on s.id = d.step
							and d.identifier = 'x'
							and d.kind = 'new_state'
					where d.value <> 0
				) x on s.id = x.id
		where r.nivel_function = 1010151 -- 1 = 1 -- r.nivel_function = $run_id 
			and d.kind = 'new_state' 
		order by d.value desc
	"

config$groups_query = "
		set nocount on 
		select distinct group_identifier 
		from data.simulient_step s 
			inner join data.simulient_run r on s.run = r.id 
		where r.nivel_function = $run_id 
		"

config$metrics_query = "
		set nocount on 
		select distinct d.identifier
		from data.simulient_step s 
			inner join data.simulient_run r on s.run = r.id 
			inner join data.simulient_detail d on s.id = d.step
		where r.nivel_function = $run_id 
		"

config$runs_query = "
		set nocount on
		declare @experiment int = $experiment_id 
		select t.entity as run
		from nivel.reference_targets t 
		where t.source = @experiment 
			and t.identifier = 'run_experiment' 
		order by t.target_id desc
		"

config$aggregate_by_heatmap = selectInput('aggregate_by', 'Aggregate by', 
		c('Day' = 'date', 
		'Week' = 'week_label', 
		'Month' = 'month_label'))

config$aggregate_by_lines = selectInput('aggregate_by', 'Aggregate by', 
		c(
			'None' = 'none',
			'5 min' = 'agg_5_min', 
			'15 min' = 'agg_15_min',
			'30 min' = 'agg_30_min',
			'Hour' = 'hours',
			'Day' = 'date',
			'Week' = 'week_label', 
			'Month' = 'month_label'),
		selected = 'hours')

config$page_title = 'xCESE Experiment Results'

config$lang_list_of_runs = 'List of runs'
config$lang_groups = 'Groups'
config$lang_metrics = 'Metrics'
config$lang_chart_type = 'Chart type'
config$lang_chart_choice_names = c("Lines", "Heatmap")
config$lang_refresh_data = "Refresh data"
config$lang_weekdays = c("maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai", "sunnuntai")

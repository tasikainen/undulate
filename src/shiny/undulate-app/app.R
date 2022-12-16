library(httr)
library(jsonlite)
library(shiny)
library(plotly)
library(RColorBrewer)

# Process the file env.txt in the application folder
# The file is produced by run-shiny.sh based on setenv.sh (variables defined therein)
processFile = function(filepath) {
  ret = list()
  con = file(filepath, "r")
  while ( TRUE ) {
    x = readLines(con, n = 1)
    if ( length(x) == 0 ) {
      break
    }
    v=strsplit(x,"=")[[1]]
    ret[[v[1]]] = substr(x,nchar(v[1])+2,nchar(x))
  }

  ret
}

env.vals = processFile("env.txt")

# In the development setting, this is overridden in run.r
# when the url is reset after sourcing this file and before running the app using sh$url = config$datapi_url
source('config.r')

url = as.character(env.vals[['DATAPI_URL_ON_HOST']])

roundDate = function(date, level) {
	if (is.na(level) || level == 'none') {
		return(date)
	}

	if (level %in% c("secs", "mins", "hours", "days", "months")) {
		return(as.POSIXct(round(date, level)))
	}

	parts = unlist(strsplit(level, "_"))
	multiple = as.integer(parts[2])
	unit = parts[3]
	
	daypart = format(date, "%Y-%m-%d")

	minute = as.integer(format(date, "%M"))
	hour = as.integer(format(date, "%H"))
	second = as.integer(format(date, "%S"))

	if (unit == "min") {
		minute = minute - (minute %% multiple)
		second = 0
	} else if (unit == "hour") {
		hour = hour - (hour %% multiple)
		minute = 0
		second = 0
	} else if (unit == "sec") {
		second = second - (second %% multiple)
	}

	as.POSIXct(paste(daypart, paste(hour, minute, second, sep = ':'), try = "%Y-%m-%d %H:%M:%S"), tz = "UTC")
}

queryDataWithAPI = function(url = "", queryText, datecols = c(), intcols = c(), numcols = c(), dateformat = "%d/%m/%Y %H:%M:%S") { 
	res = POST(url, body = list(query=queryText), encode = 'json')
	resobj = jsonlite::fromJSON(content(res, 'text'))

	if ("data" %in% names(resobj)) {
		df = as.data.frame(resobj$data$rows, stringsAsFactors = FALSE)
		colnames(df) = resobj$data$columns
	} else {
		df = as.data.frame(resobj$rows, stringsAsFactors = FALSE)
		colnames(df) = resobj$columns
	}

	for (dc in datecols) {
		df[[dc]] = as.POSIXct(as.character(df[[dc]]), try = dateformat, tz = "UTC")
	}

	for (dc in numcols) {
		df[[dc]] = as.numeric(df[[dc]])
	}

	for (dc in intcols) {
		df[[dc]] = as.integer(df[[dc]])
	}

	df
}

ui <- uiOutput("ui")

server <- function(input, output, session) {
  periodic <- reactive({
	invalidateLater(60 * 1000, session)
	input$refreshButton
	max(queryDataWithAPI(url, "exec sp_test 'r-periodic'"))
  })

  login = FALSE
  shiny_user <- reactiveValues(login = login, failed = FALSE) #define it outside
  basic_data <- reactiveValues(fetched = FALSE, metric_values = NULL, metric_names = NULL, 
	group_values = NULL, group_names = NULL, date = c(), week_label = c(), month_label = c(), 
	experiment_id = NULL, default_run = NULL, runs = NULL)

  df <- reactive({
	print("fetching data")

	# How to get the for ... in stuff: cat(paste('[', 0:23, ']', sep = ''), sep = ', ')
	queryText = config$data_query
	queryText = sub("\\$run_id", basic_data$default_run, queryText)

	df = queryDataWithAPI(url, queryText, datecols = c('tstamp', 'date'), numcols = 'value', intcols = c('day_of_month', 'day_of_week', 'week', 'month', 'minute', 'hour', 'year', 'minute'))

	# Should have the series variable and series name (shown in the legend) separately
	# Or paste the labels based on a unique separator (that doesn't appear in group or variable name; _ may appear)
	df$series = paste(as.character(df$group_id), as.character(df$variable), sep = '_')

	# print(df)

	df
  })

  observe({
	# Update the metrics and groups based on the run ID
	print(paste("observe basic_data$default_run, update variables and groups: run_id =", input$run_id))

	basic_data$default_run = input$run_id

	if (!is.null(basic_data$default_run)) {	
		run_data = getRunParameterData(basic_data$default_run)

		basic_data$group_values = run_data$groups$group_identifier
		basic_data$group_names = run_data$groups$group_identifier
		basic_data$metric_values = run_data$metrics$identifier
		basic_data$metric_names = run_data$metrics$identifier
	}
  })

  getRunParameterData = function(run_id) {
	print(paste("getting groups and metrics for run_id", run_id))
	# A standard function (non-reactive) for fetching metrics and group data from the database
	# CONF This depends on the kind of data used (application)

	print(run_id)
	get_groups_query = config$groups_query
	get_groups_query = sub("\\$run_id", run_id, get_groups_query)
	groups = queryDataWithAPI(url, queryText = get_groups_query)

	# print("groups")
	# print(groups)
						
	# List of metrics/variables
	# CONF This depends on the kind of data used (application)
	get_metrics_query = config$metrics_query
	get_metrics_query = sub("\\$run_id", run_id, get_metrics_query)
	metrics = queryDataWithAPI(url, queryText = get_metrics_query)

	list(groups = groups, metrics = metrics)
  }

  observe({ 
	# Observer for logins
	# This wasn't part of the original thing, just needed for the essentially constant experiment ID being represented
	query <- parseQueryString(session$clientData$url_search)
	basic_data$experiment_id = paste(query['experiment_id']) # This works

	# The login option would not be necessary, so should jump to the success part without further ado
	if (shiny_user$login == FALSE) {
		if (!is.null(input$loginButton)) {
			if (input$loginButton > 0) {
				username <- isolate(input$username)
				password <- isolate(input$password)
				# if(length(which(credentials$username_id == Username)) == 1) { 
				if (username == 'admin') { # NB
					# pasmatch	<- credentials["passod"][which(credentials$username_id == username),]
					# pasverify <- password_verify(pasmatch, password)
					if (password == 'xcese') { # (pasverify) {
						shiny_user$login <- TRUE
						get_runs_query = config$runs_query 
						get_runs_query = gsub("\\$experiment_id", basic_data$experiment_id, get_runs_query)
						runs = queryDataWithAPI(url, queryText = get_runs_query)
						basic_data$default_run = runs$run[1]
						basic_data$runs = runs # These need not be updated at this point

						run_data = getRunParameterData(basic_data$default_run)

						basic_data$group_values = run_data$groups$group_identifier
						basic_data$group_names = run_data$groups$group_identifier
						basic_data$metric_values = run_data$metrics$identifier
						basic_data$metric_names = run_data$metrics$identifier
					} else {
						# Password incorrect
						shiny_user$failed <- TRUE
						# shinyjs::toggle(id = "nomatch", anim = TRUE, time = 1, animType = "fade")
						# shinyjs::delay(3000, shinyjs::toggle(id = "nomatch", anim = TRUE, time = 1, animType = "fade"))
					}
				} else {
						# User not found
						shiny_user$failed <- TRUE
					# shinyjs::toggle(id = "nomatch", anim = TRUE, time = 1, animType = "fade")
					# shinyjs::delay(3000, shinyjs::toggle(id = "nomatch", anim = TRUE, time = 1, animType = "fade"))
				}
			} 
		}
	}		
  })

  output$ui <- renderUI({
	# Reactive with respect to user and basic_data$group_* and $metric_*
	aggregate_by_heatmap = config$aggregate_by_heatmap
	aggregate_by_lines = config$aggregate_by_lines

	if (!shiny_user$login) {
		failedText = ""
		if (shiny_user$failed) {
			failedText = p("Login failed")
		}
		fluidPage(
			# CONF
			headerPanel(config$page_title),
			textInput('username', "User name"),
			passwordInput('password', 'Password'),
			actionButton('loginButton', 'Login'),
			failedText,
		    	imageOutput("image_test")
		)
	} else {
	fluidPage(
		headerPanel(config$page_title),
		sidebarPanel(
			selectInput('run_id', config$lang_list_of_runs, basic_data$runs, selected = basic_data$default_run),
			checkboxGroupInput("groups", config$lang_groups, 
					choiceNames = basic_data$group_names, 
					choiceValues = basic_data$group_values,
					selected = basic_data$group_values[1]),
			# CONF
			checkboxGroupInput("metrics", config$lang_metrics,
					choiceNames = basic_data$metric_names, 
					choiceValues = basic_data$metric_values,
					selected = basic_data$metric_values[1]),
			radioButtons("chart_type", label = config$lang_chart_type, choiceNames = config$lang_chart_choice_names, 
				choiceValues = c("line", "heatmap")),
			aggregate_by_lines,
			actionButton("refreshButton", config$lang_refresh_data, class = "btn-success")
		), # sidebarPanel
		mainPanel(
			plotlyOutput('plotly'),
			textOutput('input_data')
		)
	) # fluidPage
	}
  })

  output$plotly <- renderPlotly({
	print("rendering graphics")
	# Reacts to groups and metrics selections
	# Probably also if the input panel is rendered
	# Also to df() - the data frame
		output = c()
		for (name in names(input)[grep("groups", names(input))]) {
			output = c(output, input[[name]])
		}
		t_groups = output

		output = c()
		for (name in names(input)[grep("metrics", names(input))]) {
			output = c(output, input[[name]])
		}
		t_metrics = output

	if (input$chart_type == "heatmap") {
		clist = list(date = "hour", week_label = "day_of_week", month_label = "day_of_month")
		ylabels = list(date = 0:23, week_label = config$lang_weekdays, month_label = 1:31)

		level = input$aggregate_by # This is the parameter
		if (!level %in% names(clist)) {
			level = 'date'
		}
		detail = clist[[level]]

		dff = df()
		redu = dff[Reduce("&", list(dff$variable %in% t_metrics, dff$group_id %in% t_groups)),]

		fo = formula(paste("value ~ ", level, '+', detail ))
		ag = aggregate(fo, redu, mean)
		wi = reshape(ag, v.names = 'value', timevar = detail, idvar = level, direction = 'wide')
		rownames(wi) = wi[[level]]

		wi2 = data.frame(wi[[level]])
		rownames(wi2) = rownames(wi)
		colnames(wi) = sub("value.", "", colnames(wi))
		for (i in 1:length(ylabels[[level]])) {
			ylab = as.character(ylabels[[level]][i])
			if (i %in% colnames(wi)) {
				wi2[[ylab]] = wi[[as.character(i)]]
			} else {
				wi2[[ylab]] = NA
			}
		}
		wi2=wi2[,2:dim(wi2)[2]] # remove the first column, the seed

		if (level == 'date') {
			full_labels = unique(format(basic_data[[level]], "%Y-%m-%d"))
		} else {
			full_labels = unique(basic_data[[level]])
		}
		for (label in full_labels) {
			if (!label %in% rownames(wi2)) {
				wi2[label,] = NA
			}
		}
		wi2=wi2[sort(rownames(wi2)),]

		palette <- colorRampPalette(c("green", "yellow", "red")) # "darkblue", "blue", "lightblue1", "green","yellow", "red", "darkred"))
		p <- plot_ly(z = t(wi2), type = 'heatmap', x = rownames(wi2), y = colnames(wi2), colors = palette(50))
		p <- p %>% layout(yaxis = list(autorange = "reversed"), xaxis = list(type = "category"))
		p
	} else {
		# Line chart
		# dff = df

		level = input$aggregate_by
		dff = df()

		# print(dff)
		print(level)
		print(t_metrics)
		print(t_groups)

		if (!level %in% names(dff)) {
			dff[[level]] = roundDate(dff$tstamp, level)
		}

		colnames(dff)[which(colnames(dff)==level)] = 'x_data'
		fo = formula(paste("value ~", 'x_data', "+ series", sep = ''))
		agge = aggregate(fo, dff[Reduce("&", list(dff$variable %in% t_metrics, dff$group_id %in% t_groups)),], mean)

		# Now drawing by default with plot_ly
		if (TRUE) {
			p <- plot_ly()%>%
				layout(title = paste("Values for experiment run with id", basic_data$default_run),
					xaxis = list(title = ""),
					yaxis = list (title = "") 
				)

			for (ser in unique(agge$series)) {
				p <- p %>% add_trace(x = agge[agge$series == ser, "x_data"], 
					y = agge[agge$series == ser, "value"], name = ser,
					type = 'scatter',
					mode = 'line+markers',
					line = list(color = 'rgb(205, 12, 24)', width = 2))
			}
			p
		} else {
			# This doesn't work if the x-values are not numeric or dates
			ggplotly(ggplot(data = agge, aes(x=x_data, y = value)) + geom_line(aes(colour=series)))
		}
	}
  })

  output$input_data <- renderText({
	periodic()
  })
}

shinyApp(ui,server)

  

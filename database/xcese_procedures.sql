create schema xcese authorization dbo
go
 
if object_id('xcese.sp_routings_active_get') is not null drop procedure xcese.sp_routings_active_get
go
create procedure xcese.sp_routings_active_get
(
	@experiment int = null,
	@service varchar(63) = null
)
as
begin
	set nocount on

	-- This procedure returns

	-- Not all are used in each procedure, but include them just in case
	declare @service_base_type int, @experiment_base_type int, @simulient_configuration int, @experiment_group_base_type int, @user_group_base_type int
	select @service_base_type = id from nivel.entity where identifier = '__service_base_type'
	select @experiment_base_type = id from nivel.entity where identifier = '__experiment_base_type'
	select @experiment_group_base_type = id from nivel.entity where identifier = '__experiment_group_base_type'
	select @simulient_configuration = id from nivel.entity where identifier = '__simulient_configuration'
	select @user_group_base_type = id from nivel.entity where identifier = '__user_group_base_type'

	if object_id('tempdb..#test') is not null drop table #test
	select z.entity, t.entity as group_id, x.value as repository, y.value as tag, s.value as start_time, g.value as service, o.value as end_time
	into #test
	from nivel.entity e
		inner join nivel.instance_of i on e.id = i.instance
		inner join nivel.reference_targets t on e.id = t.source
			and t.identifier in ('control_group', 'test_group')
		inner join nivel.reference_targets u on t.entity = u.source
			and u.identifier = 'implementation'
		inner join nivel.value x on u.entity = x.entity
			and x.identifier = 'repository'
		inner join nivel.value y on u.entity = y.entity
			and y.identifier = 'tag'
		inner join nivel.value g on u.entity = g.entity
			and g.identifier = 'service'
		inner join
			(
				select v.entity, v.value
				from nivel.instance_of i
					inner join nivel.entity e on i.instance = e.id
					inner join nivel.value v on e.id = v.entity
						and v.identifier = 'service_name'
				where i.type = @service_base_type 
			) z on g.value = z.value
		inner join nivel.value s on e.id = s.entity
			and s.identifier = 'start_time'
		inner join nivel.value o on e.id = o.entity
			and o.identifier = 'end_time'
	where i.type = @experiment_base_type 
		and e.id = isnull(@experiment, e.id)
	order by t.entity desc

	select entity, service, '[''' + string_agg(group_id, ''',''') + ''']' as test_groups
	from #test
	where service = isnull(@service, service)
	group by entity, service
end
go
grant execute on xcese.sp_routings_active_get to webuser
go

if object_id('xcese.sp_experiments_active_get') is not null drop procedure xcese.sp_experiments_active_get
go
create procedure xcese.sp_experiments_active_get
(
	@format varchar(15) = 'lines'
)
as
begin
	set nocount on

	-- Not all are used in each procedure, but include them just in case
	declare @service_base_type int, @experiment_base_type int, @simulient_configuration int, @experiment_group_base_type int, @user_group_base_type int
	select @service_base_type = id from nivel.entity where identifier = '__service_base_type'
	select @experiment_base_type = id from nivel.entity where identifier = '__experiment_base_type'
	select @experiment_group_base_type = id from nivel.entity where identifier = '__experiment_group_base_type'
	select @simulient_configuration = id from nivel.entity where identifier = '__simulient_configuration'
	select @user_group_base_type = id from nivel.entity where identifier = '__user_group_base_type'

	if object_id('tempdb..#test') is not null drop 
	table #test
	select distinct e.id as entity -- t.entity as group_id, x.value as repository, y.value as tag, s.value as start_time, g.value as service, o.value as end_time
	into #test
	-- select *
	from nivel.entity e
		inner join nivel.instance_of i on e.id = i.instance
		inner join nivel.reference_targets t on e.id = t.source
			and t.identifier in ('test_group')
	where i.type = @experiment_base_type 
		and t.entity is not null
	order by e.id desc

	if @format = 'lines'
		select * 
		from #test
	else
		select '[''' + string_agg(entity, ''',''') + ''']' as experiments
		from #test
end
go
grant execute on xcese.sp_experiments_active_get to webuser
go

if object_id('xcese.sp_function_history_clear') is not null drop procedure xcese.sp_function_history_clear
go
create procedure xcese.sp_function_history_clear
(
	@reference int
)
as
begin
	declare @run_entity table ( id int )
	insert into @run_entity(id)
		select entity
		from nivel.reference_target 
		where reference = @reference

	while @@rowcount > 0
		-- Traverse the references too in order to make delete from nivel.entity work
		insert into @run_entity(id)
			select distinct t.entity
			from @run_entity e
				inner join nivel.reference_targets t on e.id = t.source
				left outer join @run_entity x on t.entity = x.id
			where x.id is null

	-- 2022-10-06 NB It is still assumed that there are no attributes, generalisations etc. in the entities
	-- 2022-10-19 The edit doesn't seem to be enough, but must leave it for later

	delete v
	from nivel.value v
	where v.entity in (select id from @run_entity)

	delete i
	from nivel.instance_of i
	where i.instance in (select id from @run_entity)

	delete t
	from nivel.reference_target t
	where t.entity in (select id from @run_entity)
		and t.reference = @reference

	delete e
	from nivel.entity e
	where e.id in (select id from @run_entity)
end
go
grant execute on xcese.sp_function_history_clear to webuser
go

-- rollback

if object_id('xcese.sp_step_experiment_round') is not null drop procedure xcese.sp_step_experiment_round
go
create procedure xcese.sp_step_experiment_round
(
	@experiment int
)
as
begin
	set nocount on

	-- Not all are used in each procedure, but include them just in case
	declare @service_base_type int, @experiment_base_type int, @simulient_configuration int, @experiment_group_base_type int, @user_group_base_type int
	select @service_base_type = id from nivel.entity where identifier = '__service_base_type'
	select @experiment_base_type = id from nivel.entity where identifier = '__experiment_base_type'
	select @experiment_group_base_type = id from nivel.entity where identifier = '__experiment_group_base_type'
	select @simulient_configuration = id from nivel.entity where identifier = '__simulient_configuration'
	select @user_group_base_type = id from nivel.entity where identifier = '__user_group_base_type'

	insert into nivel.request(request, entity, mode)
	values ('xcese.sp_step_experiment_round', @experiment, null)

	declare @implementation_entity int, @control_group_entity int
	select @control_group_entity = x.source, @implementation_entity = x.entity
	from nivel.reference_targets t
		inner join nivel.reference_targets x on t.entity = x.source
			and x.identifier = 'implementation'
	where t.source = @experiment
		and t.identifier = 'control_group'

	-- Add references to the experiment in case they are missing
	insert into nivel.reference(source, identifier, name, parent, potency)
		select @experiment, r.identifier, r.name, r.id as parent, r.potency - 1
		from nivel.instance_of i
			inner join nivel.reference r on i.type = r.source
			left outer join nivel.reference x on i.instance = x.source
				and r.id = x.parent
		where i.instance = @experiment
			and x.id is null

	-- ensin insertoitava muuttujat
	-- sitten vietävä näille vastaavat nimet ja arvot, 1:1
	declare @variable table ( id_in_cc int, var_key varchar(31) ) 
	insert into @variable(id_in_cc, var_key)
		select t.entity, v.value
		from nivel.reference_targets t
			inner join nivel.value v on t.entity = v.entity
				and v.identifier = 'key'
		where t.source = @control_group_entity
			and t.identifier = 'variables'

	declare @running table ( id int identity(3000,1) primary key, identifier varchar(63), reference_target int, group_id int, age int, control_or_test varchar(15) ) 

	insert into @running(reference_target, identifier, group_id, age, control_or_test)
		select t.id, g.identifier, g.id, datediff(s, g.created, getdate()) as age, r.identifier
		from nivel.reference r
			inner join nivel.reference_target t on r.id = t.reference
			inner join nivel.entity g on t.entity = g.id
		where r.source = @experiment -- the experiment entity
			and r.identifier in ('test_group', 'control_group')
			--and datediff(s, g.created, getdate()) between 15 and 3600 -- save the old for now, should create a new experiment instance for this

	declare @completed_group_reference int
	select  @completed_group_reference = id
	from nivel.reference 
	where source = @experiment
		and identifier = 'completed_group'

	-- TODO To be replaced with: remove the experiment groups that have been marked as completed (another process for that)
	-- also should move the completed groups under another reference; these could be likewise checked
	declare @to_be_deleted table ( id int, entity int )
	insert into @to_be_deleted(id, entity)
		select t.id, t.entity -- , 'to_be_deleted'
		from nivel.reference_target t
			inner join @running r on t.id = r.reference_target
		where age > 120 -- between 120 and 86400 -- NB These could be parameterized; better still, rely on statuses updated elsewhere
			and r.control_or_test <> 'control_group'

	delete t
	from nivel.reference_target t
		inner join @to_be_deleted x on t.id = x.id

	-- add the deleted groups as reference targets under the completed_groups
	insert into nivel.reference_target(reference, entity)
		select @completed_group_reference, x.entity
		from @to_be_deleted x

	-- Delete the simulient groups from the simulient configuration that correspond to groups being deleted from the experiment (after completion)
	delete z
	-- select x.entity, t.entity, 'deleted simulient groups', u.*, z.id
	from @to_be_deleted x
		inner join nivel.reference_targets t on x.entity = t.source
			and t.identifier = 'simulient_group'
		inner join nivel.reference_targets u on t.entity = u.entity
			and u.source = @simulient_configuration
		inner join nivel.reference_target z on u.target_id = z.id

	declare @max_x int
	select @max_x = max(cast(s.value as int))
	from @running r
		inner join nivel.reference_targets v on r.group_id = v.source -- variables
			and v.identifier = 'variables'
		inner join nivel.value u on v.entity = u.entity
			and u.identifier = 'key'
			and u.value = 'x'
		inner join nivel.value s on u.entity = s.entity
			and s.identifier = 'value'

	-- If the extreme value of the variable has not been reached and there is space for new experiments,
	-- add new groups
	if @max_x < 20 and (select count(*) from @running) - (select count(*) from @to_be_deleted) < 4
	begin
		-- Create a new group
		declare @test_group_reference int
		select  @test_group_reference = id
		from nivel.reference 
		where source = @experiment
			and identifier = 'test_group'

		declare @x int = @max_x + 1

		insert into nivel.entity(identifier, name)
			select 'test_group_x_' + cast(@x as varchar), 'Test group with x = ' + cast(@x as varchar)

		declare @group_inserted int = @@identity

		declare @group_experiment_base_type int = @experiment_group_base_type

		insert into nivel.instance_of(instance, type)
		values (@group_inserted, @group_experiment_base_type)

		declare @test_group_parent int
		select @test_group_parent = id
		-- select *
		from nivel.reference
		where source = @group_experiment_base_type

		-- Insert the references for the newly created group based on the type's references
		insert into nivel.reference(source, identifier, name, parent, potency)
			select @group_inserted, r.identifier, r.name, r.id as parent, r.potency - 1
			from nivel.reference r
			where source = @group_experiment_base_type

		-- Insert reference to the pre-existing implementation (copy target from control group)
		-- TODO Extend to cover multiple implementations
		insert into nivel.reference_target(reference, entity)
			select r.id, @implementation_entity
			from nivel.reference r
			where r.source = @group_inserted
				and r.identifier = 'implementation'

		-- Variables
		-- Nämä olisi kopioitava control_group:sta
		-- Voi olla useita
		declare @variable_inserted table ( id int )
		insert into nivel.entity(identifier, name, description)
		output inserted.id into @variable_inserted(id)
			select v.var_key, 'Variable ' + v.var_key, v.id_in_cc
			from @variable v
			order by v.var_key

		-- add reference targets for the inserted variable entities
		insert into nivel.reference_target(reference, entity)
			select r.id, i.id
			from nivel.reference r
				cross join @variable_inserted i
			where r.source = @group_inserted
				and r.identifier = 'variables'

		declare @variable_type int
		select @variable_type = i.type
		from @variable v
			inner join nivel.instance_of i on v.id_in_cc = i.instance

		insert into nivel.instance_of(instance, type)
			select i.id, @variable_type
			from @variable_inserted i

		-- insert the variable keys
		insert into nivel.value(entity, identifier, name, value, attribute)
			select i.id, k.identifier, k.name, k.value, k.attribute
			from @variable_inserted i
				inner join nivel.entity e on i.id = e.id
				inner join nivel.value k on cast(e.description as int) = k.entity
					and k.identifier = 'key'

		-- insert the variable values
		insert into nivel.value(entity, identifier, name, value, attribute)
			select 
				i.id, v.identifier, v.name, 
				case when k.value = 'x' then @max_x + 1 else v.value end as value, 
				v.attribute
			from @variable_inserted i
				inner join nivel.entity e on i.id = e.id
				inner join nivel.value k on cast(e.description as int) = k.entity
					and k.identifier = 'key'
				inner join nivel.value v on k.entity = v.entity
					and v.identifier = 'value'

		-- Insert the new group as a target for the test_group reference of the experiment
		insert into nivel.reference_target(reference, entity)
		values (@test_group_reference, @group_inserted)

		-- select @group_inserted as group_inserted

		-- Add a corresponding definition under a relevant simulient configuration
		-- TODO Should probably define as a part of the 
		declare @simulient_users_reference int = (select id from nivel.reference where source = @simulient_configuration and identifier = 'users')

		insert into nivel.entity(identifier, name)
			select 'user_group_g' + cast(@group_inserted as varchar), 'Simulient group for group g' + cast(@group_inserted as varchar)

		declare @simulient_group int = @@identity

		insert into nivel.instance_of(instance, type)
		values (@simulient_group, @user_group_base_type) 
		-- - Or maybe there is could be an easier way to do this, using a procedure or something

		insert into nivel.reference_target(reference, entity)
		values (@simulient_users_reference, @simulient_group)

		-- Add the values for the group
		-- There should be a function for this as well; the attributes are needed
		insert into nivel.value(entity, identifier, name, attribute, value)
			select 
				@simulient_group, a.identifier, a.name, a.id,
				case a.identifier 
					when 'group' then 'g'
					when 'group_id' then 'g' + cast(@group_inserted as varchar)
					when 'number_of_users' then cast(5 as varchar)
					end
			from nivel.instance_of i
				inner join nivel.attribute a on i.type = a.entity
					and a.potency = 1
					and a.identifier in ('group', 'group_id', 'number_of_users')
			where i.instance = @simulient_group

		-- add a reference to the created simulient group under the experiment group
		insert into nivel.reference_target(reference, entity)
			select r.id, @simulient_group
			from nivel.reference r
			where r.source = @group_inserted
				and r.identifier = 'simulient_group'
	end
end
go
grant execute on xcese.sp_step_experiment_round to webuser
go

if object_id('xcese.sp_experiment_init') is not null drop procedure xcese.sp_experiment_init
go
create procedure xcese.sp_experiment_init
(
	@experiment int,
	@function int = null -- TODO should be able to get the function/action parameters so that log can be written from the database as well
)
as
begin
	set nocount on

	-- Not all are used in each procedure, but include them just in case
	declare @service_base_type int, @experiment_base_type int, @simulient_configuration int, @experiment_group_base_type int, @user_group_base_type int
	select @service_base_type = id from nivel.entity where identifier = '__service_base_type'
	select @experiment_base_type = id from nivel.entity where identifier = '__experiment_base_type'
	select @experiment_group_base_type = id from nivel.entity where identifier = '__experiment_group_base_type'
	select @simulient_configuration = id from nivel.entity where identifier = '__simulient_configuration'
	select @user_group_base_type = id from nivel.entity where identifier = '__user_group_base_type'

	-- Move all the groups except the control group under completed as a part of initialising the experiment
	declare @running table ( id int identity(3000,1) primary key, identifier varchar(63), reference_target int, group_id int, age int, control_or_test varchar(15) ) 

	insert into @running(reference_target, identifier, group_id, age, control_or_test)
		select t.id, g.identifier, g.id, datediff(s, g.created, getdate()) as age, r.identifier
		from nivel.reference r
			inner join nivel.reference_target t on r.id = t.reference
			inner join nivel.entity g on t.entity = g.id
		where r.source = @experiment -- the experiment entity
			and r.identifier in ('test_group', 'control_group')
			--and datediff(s, g.created, getdate()) between 15 and 3600 -- save the old for now, should create a new experiment instance for this

	declare @completed_group_reference int
	select  @completed_group_reference = id
	from nivel.reference 
	where source = @experiment
		and identifier = 'completed_group'

	declare @to_be_deleted table ( id int, entity int )
	insert into @to_be_deleted(id, entity)
		select t.id, t.entity -- , 'to_be_deleted'
		from nivel.reference_target t
			inner join @running r on t.id = r.reference_target
		where r.control_or_test <> 'control_group'
			-- and age between 120 and 86400 -- NB These could be parameterized; better still, rely on statuses updated elsewhere

	delete t
	from nivel.reference_target t
		inner join @to_be_deleted x on t.id = x.id

	insert into nivel.request(request, entity, mode)
	values ('xcese.sp_experiment_init', @experiment, null)

	exec xcese.sp_step_experiment_round @experiment
end
go
grant execute on xcese.sp_experiment_init to webuser
go

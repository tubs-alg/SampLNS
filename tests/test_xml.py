import io

from samplns.instances.parser import parse_source


def test_hello_world_with_descriptions():
    xml_string = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<featureModel>
	<properties>
		<calculations key="tautology" value="true"/>
		<calculations key="auto" value="true"/>
		<graphics key="showconstraints" value="true"/>
		<calculations key="redundant" value="true"/>
		<graphics key="showshortnames" value="false"/>
		<graphics key="layout" value="horizontal"/>
		<graphics key="legendhidden" value="false"/>
		<graphics key="layoutalgorithm" value="1"/>
		<calculations key="features" value="true"/>
		<graphics key="autolayoutconstraints" value="false"/>
		<graphics key="legendautolayout" value="true"/>
		<graphics key="showcollapsedconstraints" value="true"/>
		<calculations key="constraints" value="true"/>
	</properties>
	<struct>
		<and abstract="true" mandatory="true" name="HelloWorld">
			<feature mandatory="true" name="Hello">
				<description>Hello :)</description>
			</feature>
			<alt abstract="true" name="Feature">
				<graphics key="collapsed" value="true"/>
				<feature name="Wonderful"/>
				<feature name="Beautiful">
					<description>
						Beautiful
						Description
					</description>
				</feature>
			</alt>
			<feature name="World"/>
		</and>
	</struct>
	<constraints>
		<rule>
			<tags>Tag1,Tag2</tags>
			<imp>
				<var>Feature</var>
				<var>World</var>
			</imp>
		</rule>
	</constraints>
</featureModel>
"""
    xml_file = io.StringIO(xml_string)
    instance = parse_source(xml_file, "hello_world")


def test_sandwich_with_attributes():
    xml_string = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<extendedFeatureModel>
	<properties>
		<graphics key="autolayoutconstraints" value="false"/>
		<graphics key="legendautolayout" value="true"/>
		<graphics key="showconstraints" value="true"/>
		<graphics key="showshortnames" value="false"/>
		<graphics key="layout" value="horizontal"/>
		<graphics key="showcollapsedconstraints" value="true"/>
		<graphics key="legendhidden" value="false"/>
		<graphics key="layoutalgorithm" value="1"/>
	</properties>
	<struct>
		<and mandatory="true" name="Sandwich">
			<attribute configurable="true" name="Calories" recursive="true" type="long" unit=""/>
			<attribute name="Price" recursive="true" type="double" unit="" value="0.0"/>
			<attribute name="Organic Food" recursive="true" type="boolean" unit="" value="false"/>
			<alt mandatory="true" name="Bread">
				<graphics key="collapsed" value="false"/>
				<feature name="Full Grain ">
					<attribute name="Calories" value="203"/>
					<attribute name="Price" value="1.99"/>
					<attribute name="Organic Food" value="true"/>
				</feature>
				<feature name="Flatbread">
					<attribute name="Calories" value="50"/>
					<attribute name="Price" value="1.79"/>
					<attribute name="Organic Food" value="true"/>
				</feature>
				<feature name="Toast">
					<attribute name="Calories" value="313"/>
					<attribute name="Price" value="1.79"/>
					<attribute name="Organic Food" value="false"/>
				</feature>
			</alt>
			<and name="Cheese">
				<graphics key="collapsed" value="false"/>
				<alt name="Gouda">
					<graphics key="collapsed" value="false"/>
					<feature name="Sprinkled">
						<attribute name="Calories" value="72"/>
						<attribute name="Price" value="0.49"/>
						<attribute name="Organic Food" value="true"/>
					</feature>
					<feature name="Slice">
						<attribute name="Calories" value="70"/>
						<attribute name="Price" value="0.69"/>
						<attribute name="Organic Food" value="true"/>
					</feature>
				</alt>
				<feature name="Cheddar">
					<attribute name="Calories" value="81"/>
					<attribute name="Price" value="0.69"/>
					<attribute name="Organic Food" value="false"/>
				</feature>
				<feature name="Cream Cheese ">
					<attribute name="Calories" value="52"/>
					<attribute name="Price" value="0.59"/>
					<attribute name="Organic Food" value="false"/>
				</feature>
			</and>
			<or name="Meat">
				<graphics key="collapsed" value="false"/>
				<feature name="Salami ">
					<attribute name="Calories" value="116"/>
					<attribute name="Price" value="1.29"/>
					<attribute name="Organic Food" value="true"/>
				</feature>
				<feature name="Ham">
					<attribute name="Calories" value="92"/>
					<attribute name="Price" value="0.99"/>
					<attribute name="Organic Food" value="false"/>
				</feature>
				<feature name="Chicken Breast">
					<attribute name="Calories" value="56"/>
					<attribute name="Price" value="1.39"/>
					<attribute name="Organic Food" value="true"/>
				</feature>
			</or>
			<and name="Vegetables">
				<graphics key="collapsed" value="false"/>
				<feature name="Cucumber ">
					<attribute name="Calories" value="2"/>
					<attribute name="Price" value="0.29"/>
					<attribute name="Organic Food" value="true"/>
				</feature>
				<feature name="Tomatoes">
					<attribute name="Calories" value="3"/>
					<attribute name="Price" value="0.39"/>
					<attribute name="Organic Food" value="true"/>
				</feature>
				<feature name="Lettuce">
					<attribute name="Calories" value="2"/>
					<attribute name="Price" value="0.39"/>
					<attribute name="Organic Food" value="true"/>
				</feature>
			</and>
		</and>
	</struct>
</extendedFeatureModel>
"""
    xml_file = io.StringIO(xml_string)
    instance = parse_source(xml_file, "sandwich")

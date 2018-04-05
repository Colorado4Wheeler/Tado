#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2013, Perceptive Automation, LLC. All rights reserved.
# http://www.perceptiveautomation.com

import indigo

import os
import sys
import random
import urllib2
import simplejson

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
kHvacModeEnumToStrMap = {
	indigo.kHvacMode.Cool				: u"cool",
	indigo.kHvacMode.Heat				: u"heat",
	indigo.kHvacMode.HeatCool			: u"auto",
	indigo.kHvacMode.Off				: u"off",
	indigo.kHvacMode.ProgramHeat		: u"program heat",
	indigo.kHvacMode.ProgramCool		: u"program cool",
	indigo.kHvacMode.ProgramHeatCool	: u"program auto"
}

kFanModeEnumToStrMap = {
	indigo.kFanMode.AlwaysOn			: u"always on",
	indigo.kFanMode.Auto				: u"auto"
}

def _lookupActionStrFromHvacMode(hvacMode):
	return kHvacModeEnumToStrMap.get(hvacMode, u"unknown")

def _lookupActionStrFromFanMode(fanMode):
	return kFanModeEnumToStrMap.get(fanMode, u"unknown")

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = False
		self.simulateTempChanges = True		# Every few seconds update to random temperature values
		self.simulateHumidityChanges = True	# Every few seconds update to random humidity values

	def __del__(self):
		indigo.PluginBase.__del__(self)
	
	#
	# Set state and state.ui
	#
	def setState (self, dev, statename, value):
		if dev.pluginProps["measurement"] == "C":
			# Default operation by this UK manufacturer
			stateSuffix = u" °C" 
			dev.updateStateOnServer(key=statename, value=value, decimalPlaces=1, uiValue=str(value) + stateSuffix)
		
		if dev.pluginProps["measurement"] == "F":
			# Convert
			value = float(value)
			value = (value * 1.8000) + 32
			value = round(value, 1)
			
			stateSuffix = u" °F" 
			dev.updateStateOnServer(key=statename, value=value, decimalPlaces=1, uiValue=str(value) + stateSuffix)
		

	########################################
	# Internal utility methods. Some of these are useful to provide
	# a higher-level abstraction for accessing/changing thermostat
	# properties or states.
	######################
	def _getTempSensorCount(self, dev):
		return int(dev.pluginProps["NumTemperatureInputs"])

	def _getHumiditySensorCount(self, dev):
		return int(dev.pluginProps["NumHumidityInputs"])

	######################
	def _changeTempSensorCount(self, dev, count):
		newProps = dev.pluginProps
		newProps["NumTemperatureInputs"] = count
		dev.replacePluginPropsOnServer(newProps)

	def _changeHumiditySensorCount(self, dev, count):
		newProps = dev.pluginProps
		newProps["NumHumidityInputs"] = count
		dev.replacePluginPropsOnServer(newProps)

	def _changeAllTempSensorCounts(self, count):
		for dev in indigo.devices.iter("self"):
			self._changeTempSensorCount(dev, count)

	def _changeAllHumiditySensorCounts(self, count):
		for dev in indigo.devices.iter("self"):
			self._changeHumiditySensorCount(dev, count)

	######################
	def _changeTempSensorValue(self, dev, index, value):
		# Update the temperature value at index. If index is greater than the "NumTemperatureInputs"
		# an error will be displayed in the Event Log "temperature index out-of-range"
		#stateKey = u"temperatureInput" + str(index)
		#dev.updateStateOnServer(stateKey, value, uiValue="%d °F" % (value))
		#self.debugLog(u"\"%s\" called update %s %d" % (dev.name, stateKey, value))
		X = 1

	def _changeHumiditySensorValue(self, dev, index, value):
		# Update the humidity value at index. If index is greater than the "NumHumidityInputs"
		# an error will be displayed in the Event Log "humidity index out-of-range"
		#stateKey = u"humidityInput" + str(index)
		#dev.updateStateOnServer(stateKey, value, uiValue="%d °F" % (value))
		#self.debugLog(u"\"%s\" called update %s %d" % (dev.name, stateKey, value))
		X = 1
		
	#
	# Tado request
	#
	def requestData (self, dev, command):
		if "username" in dev.pluginProps == False: return False
		if "password" in dev.pluginProps == False: return False
		
		u = dev.pluginProps["username"]
		p = dev.pluginProps["password"]
		
		try:
			f = urllib2.urlopen('https://my.tado.com/mobile/1.4/' + command + '?username=' + u + '&password=' + p)
		except:
			indigo.server.log(dev.name + ": Unable to retrieve Tado data, verify your username and password")
			return False
		
		api_data = f.read()
		data = simplejson.loads(api_data)
		
		return data
		

	######################
	# Poll all of the states from the thermostat and pass new values to
	# Indigo Server.
	def _refreshStatesFromHardware(self, dev, logRefresh, commJustStarted):
		data = self.requestData (dev, "getCurrentState")
		
		try:
			if data == False: return
		except:
			data = data
		
		housetemp = data['insideTemp']
		temp = "%.1f" % housetemp
	
		settemp = data['setPointTemp']
		set = "%.1f" % settemp
	
		self.setState (dev, "temperatureInput1", temp)
	
		if "setpointHeat" in dev.states:
			self.setState (dev, "setpointHeat", set)	
		if "setpointCool" in dev.states:
			self.setState (dev, "setpointCool", set)	
	
		dev.updateStateOnServer("operationMode", data['operation'])
		dev.updateStateOnServer("autoOperation", data['autoOperation'])
		dev.updateStateOnServer("operationTrigger", data['operationTrigger'])
		dev.updateStateOnServer("controlPhase", data['controlPhase'])
		dev.updateStateOnServer("boxConnected", data['boxConnected'])
		dev.updateStateOnServer("homeId", data['homeId'])
	
		if data['gwConnected']: 
			dev.updateStateOnServer("gatewayConnected", True)
		else:
			dev.updateStateOnServer("gatewayConnected", False)
		
		if data['tsConnected']: 
			dev.updateStateOnServer("temperatureSensorConnected", True)
		else:
			dev.updateStateOnServer("temperatureSensorConnected", False)
		
		
		#	Other states that should also be updated:
		# ** IMPLEMENT ME **
		# dev.updateStateOnServer("setpointHeat", floating number here)
		# dev.updateStateOnServer("setpointCool", floating number here)
		# dev.updateStateOnServer("hvacOperationMode", some indigo.kHvacMode.* value here)
		# dev.updateStateOnServer("hvacFanMode", some indigo.kFanMode.* value here)
		# dev.updateStateOnServer("hvacCoolerIsOn", True or False here)
		# dev.updateStateOnServer("hvacHeaterIsOn", True or False here)
		# dev.updateStateOnServer("hvacFanIsOn", True or False here)
		if logRefresh:
			try:
				if "setpointHeat" in dev.states:
					indigo.server.log(u"received \"%s\" heat setpoint update to %.1f°" % (dev.name, dev.states["setpointHeat"]))
				if "setpointCool" in dev.states:
					indigo.server.log(u"received \"%s\" cool setpoint update to %.1f°" % (dev.name, dev.states["setpointCool"]))
				if "hvacOperationMode" in dev.states:
					indigo.server.log(u"received \"%s\" main mode update to %s" % (dev.name, _lookupActionStrFromHvacMode(dev.states["hvacOperationMode"])))
				if "hvacFanMode" in dev.states:
					indigo.server.log(u"received \"%s\" fan mode update to %s" % (dev.name, _lookupActionStrFromFanMode(dev.states["hvacFanMode"])))
				if "hvacOperationMode" in dev.states:
					indigo.server.log(u"received \"%s\" main mode update to %s" % (dev.name, _lookupActionStrFromHvacMode(dev.states["hvacOperationMode"])))
			except:
				X = 1 # Placeholder to just ignore this because it is likely a new device with no data yet		
				
			
		#if parsed_json['controlPhase'] == "COOLDOWN":
	
		return
	
	######################
	# Process action request from Indigo Server to change main thermostat's main mode.
	def _handleChangeHvacModeAction(self, dev, newHvacMode):
		# Command hardware module (dev) to change the thermostat mode here:
		# ** IMPLEMENT ME **
		sendSuccess = True		# Set to False if it failed.

		actionStr = _lookupActionStrFromHvacMode(newHvacMode)
		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" mode change to %s" % (dev.name, actionStr))

			# And then tell the Indigo Server to update the state.
			if "hvacOperationMode" in dev.states:
				dev.updateStateOnServer("hvacOperationMode", newHvacMode)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" mode change to %s failed" % (dev.name, actionStr), isError=True)

	######################
	# Process action request from Indigo Server to change thermostat's fan mode.
	def _handleChangeFanModeAction(self, dev, newFanMode):
		# Command hardware module (dev) to change the fan mode here:
		# ** IMPLEMENT ME **
		sendSuccess = True		# Set to False if it failed.

		actionStr = _lookupActionStrFromFanMode(newFanMode)
		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" fan mode change to %s" % (dev.name, actionStr))

			# And then tell the Indigo Server to update the state.
			if "hvacFanMode" in dev.states:
				dev.updateStateOnServer("hvacFanMode", newFanMode)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" fan mode change to %s failed" % (dev.name, actionStr), isError=True)

	######################
	# Process action request from Indigo Server to change a cool/heat setpoint.
	def _handleChangeSetpointAction(self, dev, newSetpoint, logActionName, stateKey):
		if newSetpoint < 40.0:
			newSetpoint = 40.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
		elif newSetpoint > 95.0:
			newSetpoint = 95.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.

		sendSuccess = False

		if stateKey == u"setpointCool":
			# Command hardware module (dev) to change the cool setpoint to newSetpoint here:
			# ** IMPLEMENT ME **
			sendSuccess = True			# Set to False if it failed.
		elif stateKey == u"setpointHeat":
			# Command hardware module (dev) to change the heat setpoint to newSetpoint here:
			# ** IMPLEMENT ME **
			sendSuccess = True			# Set to False if it failed.

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" %s to %.1f°" % (dev.name, logActionName, newSetpoint))

			# And then tell the Indigo Server to update the state.
			if stateKey in dev.states:
				dev.updateStateOnServer(stateKey, newSetpoint, uiValue="%.1f °F" % (newSetpoint))
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" %s to %.1f° failed" % (dev.name, logActionName, newSetpoint), isError=True)

	########################################
	def startup(self):
		self.debugLog(u"startup called")

	def shutdown(self):
		self.debugLog(u"shutdown called")

	########################################
	def runConcurrentThread(self):
		try:
			while True:
				for dev in indigo.devices.iter("self"):
					if not dev.enabled or not dev.configured:
						continue

					# Plugins that need to poll out the status from the thermostat
					# could do so here, then broadcast back the new values to the
					# Indigo Server.
					self._refreshStatesFromHardware(dev, False, False)
					#X = 1 # placeholder
					

				self.sleep(30)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)

	########################################
	def deviceStartComm(self, dev):
		# Called when communication with the hardware should be established.
		# Here would be a good place to poll out the current states from the
		# thermostat. If periodic polling of the thermostat is needed (that
		# is, it doesn't broadcast changes back to the plugin somehow), then
		# consider adding that to runConcurrentThread() above.
		self._refreshStatesFromHardware(dev, True, True)

	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		pass

	########################################
	# Thermostat Action callback
	######################
	# Main thermostat action bottleneck called by Indigo Server.
	def actionControlThermostat(self, action, dev):
		###### SET HVAC MODE ######
		if action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
			self._handleChangeHvacModeAction(dev, action.actionMode)

		###### SET FAN MODE ######
		elif action.thermostatAction == indigo.kThermostatAction.SetFanMode:
			self._handleChangeFanModeAction(dev, action.actionMode)

		###### SET COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetCoolSetpoint:
			#newSetpoint = action.actionValue
			#self._handleChangeSetpointAction(dev, newSetpoint, u"change cool setpoint", u"setpointCool")
			indigo.server.log (dev.name + ": Changing heat/cool setpoints in Indigo not currently supported, please use the Tado or the Tado app")

		###### SET HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint:
			#newSetpoint = action.actionValue
			#self._handleChangeSetpointAction(dev, newSetpoint, u"change heat setpoint", u"setpointHeat")
			indigo.server.log (dev.name + ": Changing heat/cool setpoints in Indigo not currently supported, please use the Tado or the Tado app")

		###### DECREASE/INCREASE COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint - action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"decrease cool setpoint", u"setpointCool")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint + action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"increase cool setpoint", u"setpointCool")

		###### DECREASE/INCREASE HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint:
			#newSetpoint = dev.heatSetpoint - action.actionValue
			#self._handleChangeSetpointAction(dev, newSetpoint, u"decrease heat setpoint", u"setpointHeat")
			indigo.server.log (dev.name + ": Changing heat/cool setpoints in Indigo not currently supported, please use the Tado or the Tado app")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint:
			#newSetpoint = dev.heatSetpoint + action.actionValue
			#self._handleChangeSetpointAction(dev, newSetpoint, u"increase heat setpoint", u"setpointHeat")
			indigo.server.log (dev.name + ": Changing heat/cool setpoints in Indigo not currently supported, please use the Tado or the Tado app")
		
		###### REQUEST STATE UPDATES ######
		elif action.thermostatAction in [indigo.kThermostatAction.RequestStatusAll, indigo.kThermostatAction.RequestMode,
		indigo.kThermostatAction.RequestEquipmentState, indigo.kThermostatAction.RequestTemperatures, indigo.kThermostatAction.RequestHumidities,
		indigo.kThermostatAction.RequestDeadbands, indigo.kThermostatAction.RequestSetpoints]:
			self._refreshStatesFromHardware(dev, True, False)

	########################################
	# General Action callback
	######################
	def actionControlGeneral(self, action, dev):
		###### BEEP ######
		if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
			# Beep the hardware module (dev) here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

		###### ENERGY UPDATE ######
		elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
			# Request hardware module (dev) for its most recent meter data here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy update request"))

		###### ENERGY RESET ######
		elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
			# Request that the hardware module (dev) reset its accumulative energy usage data here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy reset request"))

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			# Query hardware module (dev) for its current status here. This differs from the 
			# indigo.kThermostatAction.RequestStatusAll action - for instance, if your thermo
			# is battery powered you might only want to update it only when the user uses
			# this status request (and not from the RequestStatusAll). This action would
			# get all possible information from the thermostat and the other call
			# would only get thermostat-specific information:
			# ** GET BATTERY INFO **
			# and call the common function to update the thermo-specific data
			self._refreshStatesFromHardware(dev, True, False)
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))

	########################################
	# Custom Plugin Action callbacks (defined in Actions.xml)
	######################
	def setBacklightBrightness(self, pluginAction, dev):
		try:
			newBrightness = int(pluginAction.props.get(u"brightness", 100))
		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			indigo.server.log(u"set backlight brightness action to device \"%s\" -- invalid brightness value" % (dev.name,), isError=True)
			return

		# Command hardware module (dev) to set backlight brightness here:
		# ** IMPLEMENT ME **
		sendSuccess = True		# Set to False if it failed.

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" %s to %d" % (dev.name, "set backlight brightness", newBrightness))

			# And then tell the Indigo Server to update the state:
			dev.updateStateOnServer("backlightBrightness", newBrightness, uiValue="%d%%" % (newBrightness))
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" %s to %d failed" % (dev.name, "set backlight brightness", newBrightness), isError=True)

	########################################
	# Actions defined in MenuItems.xml. In this case we just use these menu actions to
	# simulate different thermostat configurations (how many temperature and humidity
	# sensors they have).
	####################
	def changeTempSensorCountTo1(self):
		self._changeAllTempSensorCounts(1)

	def changeTempSensorCountTo2(self):
		self._changeAllTempSensorCounts(2)

	def changeTempSensorCountTo3(self):
		self._changeAllTempSensorCounts(3)

	def changeHumiditySensorCountTo0(self):
		self._changeAllHumiditySensorCounts(0)

	def changeHumiditySensorCountTo1(self):
		self._changeAllHumiditySensorCounts(1)

	def changeHumiditySensorCountTo2(self):
		self._changeAllHumiditySensorCounts(2)

	def changeHumiditySensorCountTo3(self):
		self._changeAllHumiditySensorCounts(3)


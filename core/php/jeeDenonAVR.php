<?php

/* This file is part of Jeedom.
 *
 * Jeedom is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Jeedom is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
 */
require_once dirname(__FILE__) . "/../../../../core/php/core.inc.php";

//$apikey = jeedom::getApiKey('denonavr');

if (!jeedom::apiAccess(init('apikey'), 'denonavr')) {
	echo __('Vous n\'etes pas autorisé à effectuer cette action', __FILE__);
  log::add('denonavr', 'info', "wrong API key");
	die();
}
if (init('test') != '') {
	echo 'OK';
	die();
}

$result = json_decode(file_get_contents("php://input"), true);
if (!is_array($result)) {
	die();
}

log::add('denonavr', 'debug',"Callback call from daemon...");
$found=false;
if (isset($result['daemon'])) {
  // message from daemon
  
  //event
  if (isset($result['daemon']['event'])) {
    if ($result['daemon']['event']!="Ping") log::add('denonavr', 'info', "Callback - message from daemon: event = '" . $result['daemon']['event'] . "'");
    if ($result['daemon']['event']=='Listening') {
      // register all the eqLogics
      $devices=array();
      $eqLogics = eqLogic::byType('denonavr');
      foreach ($eqLogics as $eqLogic) {
        if ($eqLogic->getConfiguration('enableDaemon') == 1) {
          $ip = $eqLogic->getConfiguration('ip');
          $serial = strtolower($eqLogic->getConfiguration('serial'));
          $name = "Device #" . $serial;
          if (!array_key_exists($serial,$devices)) {
            log::add('denonavr', 'info', "Register serial #" . $serial ." in deamon");
            $devices[$serial]=array('serial' => $serial, 'ip' => $ip, 'name' => $name);
            $eqLogic::request('register', $devices[$serial]);
          }
        }
      }
    }
  } else {
      //other message
      log::add('denonavr', 'info', "Callback - message from daemon: " . print_r($result['daemon'], true));
    }
  $found=true;
}

if (isset($result['devices'])) {
  // message from device
  foreach ($result['devices'] as $serial => $value) {
    foreach ($value as $zone => $valueZone) {
      $zoneEqLogic = $zone;
      if (is_int($zoneEqLogic)) $zoneEqLogic = strval($zoneEqLogic);
      if ($zone == "1" || $zone == "UNDEFINED") $zoneEqLogic = "main";
      log::add('denonavr', 'debug', "Callback - zone " . $zone . " (" . $zoneEqLogic . ") => " . print_r($valueZone, true));

      // search eqLogic associated with serial and zone
      $eqlogics = eqLogic::byTypeAndSearchConfiguration('denonavr', array("serial" => $serial, "zone" => $zoneEqLogic));     
      if (is_array($eqlogics)) $eqlogic = array_pop(array_reverse($eqlogics));
        else $eqlogic = $eqlogics;
      
      foreach ($valueZone as $cmd => $valueCmd) {
        if ($cmd=='event') {
          // event
          if ($valueCmd['value']!="Ping") log::add('denonavr', 'info', "Callback - message from device '" . $serial . "', zone '" . $zone . "': event = '" . $valueCmd['value'] ."'");   
          switch ($valueCmd['value']) {
            case "Close":
              if ($eqlogic != null) {
                $eqlogic->checkAndUpdateCmd('power_state', 0);
                $eqlogic->checkAndUpdateCmd('station_name', "");
              }
              break;
          }
          if ($eqlogic != null) {
            $eqlogic->checkAndUpdateCmd('lastEvent', $valueCmd['value'] );
          }
        } elseif ($cmd=='lastMessageDate') {
            //lastMessageDate
            log::add('denonavr', 'debug', "Callback - last message or event from device '" . $serial . "': ".$valueCmd['value']);
            if ($eqlogic != null) {
              $eqlogic->checkAndUpdateCmd('lastMessage', $valueCmd['value'] );
            }
          } else {
            //cmd
            $label=$valueCmd['cmdLabel'];
            if ($zone == "UNDEFINED") {
              log::add('denonavr', 'info', "Callback - message from device '" . $serial . "': '" . $label . "' (" . $cmd . ")= '" . print_r($valueCmd['value'], true) ."'");
            } else {
                log::add('denonavr', 'info', "Callback - message from device '" . $serial . "', zone '" . $zone ."': '" . $label . "' (" . $cmd . ")= '" . print_r($valueCmd['value'], true) ."'");  
              }
            if ($eqlogic != null) {            
              log::add('denonavr', 'debug'," --> eqlogic associated with message is found: " . $eqlogic->getId());
              switch ($label) {
                case "Main Power":
                  if ($zone == "UNDEFINED") {
                    $eqlogic->checkAndUpdateCmd('power_state', ($valueCmd['value'] == 'ON') ? 1 : 0);
                    log::add('denonavr', 'debug', " --> power_state is set to '" . (($valueCmd['value'] == 'ON') ? "1" : "0") ."'");  
                  }
                  break;
                case "Power":
                  if ($zone != "UNDEFINED") {
                    $eqlogic->checkAndUpdateCmd('power_state', ($valueCmd['value'] == 'ON') ? 1 : 0);
                    log::add('denonavr', 'info', " --> power_state is set to '" . (($valueCmd['value'] == 'ON') ? "1" : "0") ."'");  
                  }
                  break;
                case "Muted":
                  $eqlogic->checkAndUpdateCmd('mute_state', ($valueCmd['value'] == true) ? 1 : 0);
                  log::add('denonavr', 'info', " --> mute_state is set to '" . (($valueCmd['value'] == true) ? "1" : "0") ."'");  
                  break;
                case "Volume":
                  $volumeRel=denonavr::volumeAbsolutetoRelative($valueCmd['value']);
                  $eqlogic->checkAndUpdateCmd('volume', $volumeRel);
                  log::add('denonavr', 'info', " --> volume (Relative) is set to '" . $volumeRel ."'");  
                  break;                  
                case "Source":
                  $input=$valueCmd['value'];
                  if (config::byKey('source_action', 'denonavr') == 'button') {
                    //convert
                    $inputNames=$eqlogic->getConfiguration('inputNames');
                    if (isset($inputNames[$input])) $input=$inputNames[$input];
                  }
                  $eqlogic->checkAndUpdateCmd('input', $input);
                  log::add('denonavr', 'info', " --> source is set to '$input' ['" . $valueCmd['value'] ."]'");  
                  break;                      
                case "Surround Mode":
                  $surround=$valueCmd['value'];
                  $eqlogic->checkAndUpdateCmd('surround', $surround);
                  log::add('denonavr', 'info', " --> surround is set to '$surround'");  
                  break;             
                case "Tuner Station Name":
                  $stationName=$valueCmd['value'];
                  $eqlogic->checkAndUpdateCmd('station_name', $stationName);
                  log::add('denonavr', 'info', " --> station_name is set to '$stationName'");  
                  break;                      
                case "Tuner Preset":
                  $preset=$valueCmd['value'];
                  $eqlogic->checkAndUpdateCmd('preset', $preset);
                  log::add('denonavr', 'info', " --> preset is set to '$preset'");  
                  break;                        
              }
            }
          }
      }
    }
  }  
  $found=true;
}

if (isset($result['infos'])) {
  // infos for device
  $eqLogics = eqLogic::byType('denononavr');
  foreach ($result['infos'] as $device => $value) {
    log::add('denonavr', 'info', "Callback - infos for device '" . $device . "': '" . print_r($value,true) ."'");
    foreach ($eqLogics as $eqLogic) {
      if ($eqLogic->getConfiguration('ip') == $device) {
        //found
        if ($eqLogic->getConfiguration('serial') != $value['serial']) {
          // update
          log::add('denonavr', 'info', "Update serial for device '" . $device . "': '" . $value['serial'] ."'");
          $eqLogic->setConfiguration('serial', $value['serial']);
          $eqLogic->save();
        }
      }
    }
  }  
  $found=true;
}

if (!$found) {
  //other
  log::add('denonavr', 'info', "Callback - " . print_r($result, true));
}


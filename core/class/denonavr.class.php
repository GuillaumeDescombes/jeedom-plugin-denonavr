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

/* * ***************************Includes********************************* */
require_once dirname(__FILE__) . '/../../../../core/php/core.inc.php';

class denonavr extends eqLogic {
	/*     * *************************Attributs****************************** */
	
	
	/*     * ***********************Methode static*************************** */
	
	public static function cron15() {
		foreach (eqLogic::byType('denonavr', true) as $eqLogic) {
			$eqLogic->updateInfo();
		}
	}
	
	/*     * *********************Méthodes d'instance************************* */
	
	public function preInsert() {
		$this->setCategory('multimedia', 1);
	}
	
	public function preUpdate() {
		if ($this->getConfiguration('ip') == '') {
			throw new Exception(__('Le champs IP ne peut etre vide', __FILE__));
		}
	}
	
	public function postSave() {
    log::add('denonavr', 'info', 'postSave()');
		$cmd = $this->getCmd(null, 'power_state');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'power_state'");
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('power_state');
			$cmd->setIsVisible(0);
			$cmd->setName(__('Etat', __FILE__));
		}
		$cmd->setType('info');
		$cmd->setSubType('binary');
		$cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "power");
		$cmd->setDisplay('generic_type', 'ENERGY_STATE');
		$cmd->save();
		$power_state_id = $cmd->getId();
		
		$cmd = $this->getCmd(null, 'input');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'input'");
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('input');
			$cmd->setIsVisible(1);
			$cmd->setName(__('Entrée', __FILE__));
		}
		$cmd->setType('info');
		$cmd->setSubType('string');
		$cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "input");
		$cmd->setDisplay('generic_type', 'GENERIC');
		$cmd->save();
		
		$cmd = $this->getCmd(null, 'volume');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'volume'");      
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('volume');
			$cmd->setIsVisible(0);
			$cmd->setName(__('Valeur Volume', __FILE__));
		}
		$cmd->setType('info');
		$cmd->setSubType('numeric');
		$cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "volume");
		$cmd->setUnite('%');
		$cmd->setDisplay('generic_type', 'LIGHT_STATE');
		$cmd->save();
		$volume_id = $cmd->getId();
		
		$cmd = $this->getCmd(null, 'sound_mode');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'sound_mode'");
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('sound_mode');
			$cmd->setIsVisible(1);
			$cmd->setName(__('Audio', __FILE__));
		}
		$cmd->setType('info');
		$cmd->setSubType('string');
		$cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "sound");
		$cmd->setDisplay('generic_type', 'GENERIC');
		$cmd->save();
		
		$cmd = $this->getCmd(null, 'volume_set');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'volume_set'");      
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('volume_set');
			$cmd->setName(__('Niveau Volume', __FILE__));
			$cmd->setIsVisible(1);
		}
		$cmd->setType('action');
		$cmd->setSubType('slider');
		$cmd->setConfiguration('minValue', config::byKey('min_volume', 'denonavr'));
		$cmd->setConfiguration('maxValue', config::byKey('max_volume', 'denonavr'));
    $cmd->setConfiguration('eqType', "volume");
		$cmd->setValue($volume_id);
		$cmd->setEqLogic_id($this->getId());
		$cmd->save();
		
		$cmd = $this->getCmd(null, 'on');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'on'");      
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('on');
			$cmd->setName(__('On', __FILE__));
			$cmd->setIsVisible(1);
			$cmd->setTemplate('dashboard', 'prise');
			$cmd->setTemplate('mobile', 'prise');
		}
		$cmd->setType('action');
		$cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "power");
		$cmd->setEqLogic_id($this->getId());
		$cmd->setDisplay('generic_type', 'ENERGY_ON');
		$cmd->setValue($power_state_id);
		$cmd->save();
		
		$cmd = $this->getCmd(null, 'off');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'off'");      
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('off');
			$cmd->setName(__('Off', __FILE__));
			$cmd->setIsVisible(1);
			$cmd->setTemplate('dashboard', 'prise');
			$cmd->setTemplate('mobile', 'prise');
		}
		$cmd->setType('action');
		$cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "power");
		$cmd->setEqLogic_id($this->getId());
		$cmd->setDisplay('generic_type', 'ENERGY_OFF');
		$cmd->setValue($power_state_id);
		$cmd->save();
		
		$cmd = $this->getCmd(null, 'refresh');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'refresh'");      
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('refresh');
			$cmd->setName(__('Rafraîchir', __FILE__));
			$cmd->setIsVisible(1);
		}
		$cmd->setType('action');
		$cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "other");
		$cmd->setEqLogic_id($this->getId());
		$cmd->save();
		
		$cmd = $this->getCmd(null, 'mute');
		if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'mute'");      
			$cmd = new denonavrCmd();
			$cmd->setLogicalId('mute');
			$cmd->setName(__('Muet', __FILE__));
			$cmd->setIsVisible(1);
		}
		$cmd->setType('action');
		$cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "volume");
		$cmd->setEqLogic_id($this->getId());
		$cmd->save();
		
		if ($this->getConfiguration('ip') != '') {
      if ($this->getConfiguration('mode') == '') {

		    $convert = array('3' => '2', '8' => '2', '9' => '2', '6' => '5', '11' => '5', '12' => '5', '13' => '5');
		    $inputModel = array(
			   '1' => array(
				  'SAT/CBL' => 'CBL/SAT',
  				'DVD' => 'DVD/Blu-ray',
	  			'BD' => 'Blu-ray',
		  		'GAME' => 'Game',
			  	'AUX1' => 'AUX',
  				'MPLAY' => 'Media Player',
	  			'USB/IPOD' => 'iPod/USB',
		  		'TV' => 'TV Audio',
			  	'TUNER' => 'Tuner',
  				'NETHOME' => 'Online Music',
	  			'BT' => 'Bluetooth',
		  		'IRP' => 'Internet Radio',
  			 ),
	  		 '7' => array(
		  		'SAT/CBL' => 'CBL/SAT',
			  	'DVD' => 'DVD/Blu-ray',
  				'GAME' => 'Game',
	  			'AUX1' => 'AUX',
		  		'MPLAY' => 'Media Player',
			  	'USB/IPOD' => 'iPod/USB',
  				'TV' => 'TV Audio',
	  			'TUNER' => 'Tuner',
		  		'NETHOME' => 'Online Music',
				  'BT' => 'Bluetooth',
  				'IRP' => 'Internet Radio',
	  			'CD' => 'CD',
		  	 ),
  			 '2' => array(
	  			'SAT/CBL' => 'CBL/SAT',
		  		'DVD' => 'DVD/Blu-ray',
			  	'BD' => 'Blu-ray',
  				'GAME' => 'Game',
	  			'AUX1' => 'AUX1',
		  		'AUX2' => 'AUX2',
				  'MPLAY' => 'Media Player',
  				'USB/IPOD' => 'iPod/USB',
	  			'TV' => 'TV Audio',
				  'TUNER' => 'Tuner',
  				'NETHOME' => 'Online Music',
	  			'BT' => 'Bluetooth',
		  		'IRP' => 'Internet Radio',
			  	'CD' => 'CD',
				  'SERVER' => 'Media Server',
  			 ),
	  		 '10' => array(
		  		'SAT/CBL' => 'CBL/SAT',
			  	'DVD' => 'DVD/Blu-ray',
  				'BD' => 'Blu-ray',
	  			'GAME' => 'Game',
		  		'AUX1' => 'AUX1',
			  	'AUX2' => 'AUX2',
				  'MPLAY' => 'Media Player',
  				'USB/IPOD' => 'iPod/USB',
	  			'TV' => 'TV Audio',
		  		'TUNER' => 'Tuner',
			  	'NETHOME' => 'Online Music',
				  'BT' => 'Bluetooth',
  				'IRP' => 'Internet Radio',
	  			'CD' => 'CD',
		  		'PHONO' => 'Phono',
			   ),
			   '4' => array(
  				'SAT/CBL' => 'CBL/SAT',
	  			'DVD' => 'DVD/Blu-ray',
		  		'BD' => 'Blu-ray',
			  	'GAME' => 'Game',
				  'AUX1' => 'AUX1',
  				'AUX2' => 'AUX2',
	  			'MPLAY' => 'Media Player',
		  		'USB/IPOD' => 'iPod/USB',
			  	'TV' => 'TV Audio',
				  'TUNER' => 'Tuner',
				  'NETHOME' => 'Online Music',
  				'BT' => 'Bluetooth',
	  			'IRP' => 'Internet Radio',
		  		'CD' => 'CD',
			  	'PHONO' => 'Phono',
			   ),
  			 '5' => array(
	  			'SAT/CBL' => 'CBL/SAT',
		  		'DVD' => 'DVD/Blu-ray',
			  	'BD' => 'Blu-ray',
  				'GAME' => 'Game',
	  			'AUX1' => 'AUX1',
		   		'AUX2' => 'AUX2',
				  'MPLAY' => 'Media Player',
  				'USB/IPOD' => 'iPod/USB',
	  			'TV' => 'TV Audio',
		  		'NETHOME' => 'Online Music',
			  	'BT' => 'Bluetooth',
				  'IRP' => 'Internet Radio',
  				'CD' => 'CD',
	  			'PHONO' => 'Phono',
		  	 ),
		    );        
        try {
    			$infos = $this->getAmpInfo();
        } catch (Exception $e) {
          }  
	  		$model = $infos['ModelId'];
			  if (isset($convert[$model])) {
  				$model = $convert[$model];
	  		}
		  	if (isset($inputModel[$model])) {
			  	foreach ($inputModel[$model] as $key => $value) {
				  	$cmd = $this->getCmd(null, $key);
  					if (!is_object($cmd)) {
              log::add('denonavr', 'info', " - creating '" . $key . "'");
		  				$cmd = new denonavrCmd();
			  			$cmd->setLogicalId($key);
				  		$cmd->setName($value);
					  	$cmd->setIsVisible(1);
					  }
					  $cmd->setType('action');
					  $cmd->setSubType('other');
            $cmd->setConfiguration('eqType', "input");
					  //$cmd->setEventOnly(1);
					  $cmd->setEqLogic_id($this->getId());
					  $cmd->save();
				  }
			  }
			  $this->updateInfo();
      } elseif ($this->getConfiguration('mode') == 'H') {
  		    $inputConverted = array(
          //INPUT NAME => INPUT ID
  				  'CBL/SAT' => 'SAT/CBL',
	    			'BLU-RAY' => 'BD',
		    		'TV AUDIO' => 'TV',
    				'MEDIA PLAYER' => 'MPLAY',
	  			  'BLUETOOTH' => 'BT'
          );
        
          try {
            $infos = $this->getAmpInfoHEOS(array("GetRenameSource", "GetDeletedSource"));
          } catch (Exception $e) {
            }
          if (isset($infos['GetRenameSource']['functionrename']['list'])) {
            foreach ($infos['GetRenameSource']['functionrename']['list'] as $list) {
              $inuse = "";
              if (isset($infos['GetDeletedSource']['functiondelete']['list'])) {
                foreach ($infos['GetDeletedSource']['functiondelete']['list'] as $ListDel) {
                  if ($ListDel['name'] == $list['name']) {
                    $inuse = $ListDel['use'];
                    break;
                  }
                }
              }
              $inputName=strtoupper($list['name']);
              if (isset($inputConverted[$inputName])) $inputID = $inputConverted[$inputName];
                else $inputID=$inputName;  
              $inputRenamed=trim($list['rename']);            
              log::add('denonavr', 'debug', " - source '" . $inputName . "': '" . $inputRenamed ."' [". $inputID ."] (" . $inuse .")");
              $cmd = $this->getCmd(null, $inputID);
  			      if (!is_object($cmd)) {
                log::add('denonavr', 'info', " - creating '" . $list['name'] . "'");
	 				      $cmd = new denonavrCmd();
	  			      $cmd->setLogicalId($inputID);
		  		      $cmd->setName($inputRenamed);
					    }
  			  	  $cmd->setIsVisible($inuse=="1"?1:0);
					    $cmd->setType('action');
					    $cmd->setSubType('other');
              $cmd->setConfiguration('eqType', "input");
					    //$cmd->setEventOnly(1);
					    $cmd->setEqLogic_id($this->getId());
					    $cmd->save();                
            }
          }  
        
        }
		}
		
	}
	
	public function getAmpInfo() {
    log::add('denonavr', 'info', 'getAmpInfo()');
	  
    $zone = '';
	  if ($this->getConfiguration('zone', 'main') == 2) {
	    $zone = '?ZoneName=ZONE2';
	  }
    $url = 'http://' . $this->getConfiguration('ip') . ':' . config::byKey('apiport_standard', 'denonavr') . '/goform/formMainZone_MainZoneXml.xml' . $zone;
    log::add('denonavr', 'debug', " - url: " . $url);
	  $request_http = new com_http($url);
    $result="";
	  try {
      $result = trim($request_http->exec());
	  } catch (Exception $e) {
   	    if ($this->getConfiguration('canBeShutdown') == 1) {
	        return;
	      } else {
	          throw new $e;
	        }
	    }
    $data=false;
    if (strpos($result, "Error 403") === false) { 
      log::add('denonavr', 'debug', " - xml: " . $result);
	    $xml = simplexml_load_string($result);
   	  $data = json_decode(json_encode($xml), true);
	    $data['VideoSelectLists'] = array();
	    if (is_array($xml->VideoSelectLists->value)) {
			  foreach ($xml->VideoSelectLists->value as $VideoSelectList) {
				  $data['VideoSelectLists'][(string) $VideoSelectList["index"]] = (string) $VideoSelectList;
			  }
	    }
	    foreach ($data as $key => $value) {
			  if (isset($value['value'])) {
				  $data[$key] = $value['value'];
			  }
	    }
    } else {
        log::add('denonavr', 'info', " - error 403");
      }

    $jsonString = json_encode($data);
    log::add('denonavr', 'debug', " - data: " . $jsonString);

	  return $data;
	}

  public function getAmpInfoAllHEOS() {
    log::add('denonavr', 'info', 'getAmpInfoAllHEOS()');

    $url = 'http://' . $this->getConfiguration('ip') . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/Deviceinfo.xml';
    log::add('denonavr', 'debug', " - url: " . $url);
    $request_http = new com_http($url);
    $result="";
    try {
      $result = trim($request_http->exec());
    } catch (Exception $e) {
        if ($this->getConfiguration('canBeShutdown') == 1) {
          return;
        } else {
            throw new $e;
          }
      }
    $data=false;
    if (strpos($result, "Error 403") === false) {
      $xml = simplexml_load_string($result);
      log::add('denonavr', 'debug', " - xml received");
      $data = json_decode(json_encode($xml), true);
      foreach ($data as $key => $value) {
        if (isset($value['value'])) {
          $data[$key] = $value['value'];
        }
      }
    } else {
        log::add('denonavr', 'info', " - error 403");
      }

    $jsonString = json_encode($data);
    log::add('denonavr', 'debug', " - data: " . $jsonString);

    return $data;
  }

  public function getAmpInfoLightHEOS() {
    log::add('denonavr', 'info', 'getAmpInfoLightHEOS()');
          
    $url = 'http://' . $this->getConfiguration('ip') . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/';
    if ($this->getConfiguration('zone', 'main') == 2) $url .= 'formZone2_Zone2XmlStatusLite.xml';
      else $url .= 'formMainZone_MainZoneXmlStatusLite.xml';
    log::add('denonavr', 'debug', " - url: " . $url);
    $request_http = new com_http($url);
    $result="";
    try {
      $result = trim($request_http->exec());
    } catch (Exception $e) {
        if ($this->getConfiguration('canBeShutdown') == 1) {
          return;
        } else {
            throw new $e;
          }
      }
    $data=false;
    if (strpos($result, "Error 403") === false) {
      $xml = simplexml_load_string($result);
      log::add('denonavr', 'debug', " - xml: " . $result);
      $data = json_decode(json_encode($xml), true);
      foreach ($data as $key => $value) {
        if (isset($value['value'])) {
          $data[$key] = $value['value'];
        }
      }
    } else {
        log::add('denonavr', 'info', " - error 403");
      }
    
    $jsonString = json_encode($data);
    log::add('denonavr', 'debug', " - data: " . $jsonString);

    return $data;
  }

  public function getAmpInfoHEOS($settings = "all") {
    log::add('denonavr', 'info', 'getAmpInfoHEOS()');
    $AllInfoHEOS = array ("GetZoneName", "GetAllZonePowerStatus", "GetAllZoneSource", "GetAllZoneVolume", "GetAllZoneMuteStatus",
                      "GetRenameSource", "GetDeletedSource", "GetSurroundModeStatus", "GetToneControl", "GetSourceStatus",
                      "GetNetAudioStatus");
    if ($settings == "all") $settings = $AllInfoHEOS;
      elseif (!is_array($settings)) $settings= array($settings);
      
    $url = 'http://' . $this->getConfiguration('ip') . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/AppCommand.xml';
    log::add('denonavr', 'debug', " - url: " . $url);
    
    $resultXMLs=false;
        
    foreach ($settings as $key => $value) {
      $postData = '<?xml version="1.0" encoding="utf-8"?>\n<tx>\n<cmd id="1">' . $value . '</cmd>\n</tx>';
    
      $request_http = new com_http($url);
      $request_http -> setPost($postData);
      $result="";
      try {
        $result = trim($request_http->exec());
      } catch (Exception $e) {
          if ($this->getConfiguration('canBeShutdown') == 1) {
            return;
          } else {
              throw new $e;
            }
        }
      if (strpos($result, "Error 403") === false) {
        $xml = simplexml_load_string($result);
        log::add('denonavr', 'debug', " - xml: " . $result);
        $resultXMLs[$value]=$xml -> cmd;
      } else {
          log::add('denonavr', 'info', " - error 403");
      }
    }
    
    $jsonString = json_encode($resultXMLs);
    log::add('denonavr', 'debug', " - json: " . $jsonString);
    $data=json_decode($jsonString, true);
    return $data;
  }
	
	public function updateInfo() {
    log::add('denonavr', 'debug', "updateInfo()");
	  if ($this->getConfiguration('ip') == '') {
	    return;
    }
    if (!$this -> isLive()) {
      log::add('denonavr', 'debug', " - isLive: false");
      $this->checkAndUpdateCmd('power_state', 0);
      $this->checkAndUpdateCmd('input', '');
      $this->checkAndUpdateCmd('sound_mode', '');
      $this->checkAndUpdateCmd('volume', -99);
      return;
    }
    
    if ($this->getConfiguration('mode') == '') {
      try {
	      $infos = $this->getAmpInfo();
	    } catch (Exception $e) {
	        return;
	      }
	    if (!is_array($infos)) {
        log::add('denonavr', 'warning', "standard API does not work. Please try HEOS API");              
	      return;
	    }
	    if (isset($infos['ZonePower'])) {
	      $this->checkAndUpdateCmd('power_state', ($infos['ZonePower'] == 'OFF') ? 0 : 1);
	    }
	    if (isset($infos['InputFuncSelect'])) {
	      $this->checkAndUpdateCmd('input', $infos['InputFuncSelect']);
	    }
	    if (isset($infos['MasterVolume'])) {
	      $this->checkAndUpdateCmd('volume', $infos['MasterVolume']);
	    }
	    if (isset($infos['selectSurround'])) {
        $this->checkAndUpdateCmd('sound_mode', $infos['selectSurround']);
	    }
    } elseif ($this->getConfiguration('mode') == 'H') {
        try {
          $infos = $this->getAmpInfoLightHEOS();
        } catch (Exception $e) {
            return;
        }
        if (!is_array($infos)) {
          log::add('denonavr', 'warning', "HEOS API does not work. Please try Standard API");
          return;
        }
        if (isset($infos['Power'])) {
          $this->checkAndUpdateCmd('power_state', ($infos['Power'] == 'OFF') ? 0 : 1);
        }
        if (isset($infos['InputFuncSelect'])) {
          $this->checkAndUpdateCmd('input', $infos['InputFuncSelect']);
        }
        if (isset($infos['MasterVolume'])) {
          $volume = $infos['MasterVolume'];
          $this->checkAndUpdateCmd('volume', $volume);
        }
        try {
          $infos = $this->getAmpInfoHEOS("GetSurroundModeStatus");
        } catch (Exception $e) {
            return;
        }
        if (!is_array($infos)) {
          log::add('denonavr', 'warning', "HEOS API does not work. Please try Standard API");
          return;
        }
        if (isset($infos['GetSurroundModeStatus']['surround'])) {
          $this->checkAndUpdateCmd('sound_mode', trim($infos['GetSurroundModeStatus']['surround']));
        }
        try {
          $infos = $this->getAmpInfoHEOS();
        } catch (Exception $e) {
            return;
        }        
        
      }
	}
  
  public function isLive() {
    log::add('denonavr', 'debug', "=> isLive()");
	  if ($this->getConfiguration('ip') == '') {
	    return false;
    }    
    $shellCmd='ping -n -c 1 -W 1 ' . $this->getConfiguration('ip');
    $request_shell = new com_shell();
    try {
      log::add('denonavr', 'debug', " - cmd: " . $shellCmd);
      $output = trim($request_shell -> execute($shellCmd));
    } catch (Exception $e) {
        // ping error => peer is not alive.
        log::add('denonavr', 'debug', "<= false");
        return false;
      }
		$output = array_values(array_filter(explode("\n",$output)));
		if (!empty($output[1])) {
			if (count($output) >= 5) {
				$response = preg_match("/time(?:=|<)(?<time>[\.0-9]+)(?:|\s)ms/", $output[count($output)-4], $matches);
				if ($response > 0 && isset($matches['time'])) {
					$latency = $matches['time'];
          log::add('denonavr', 'debug', " - latency: ". $latency . "ms");
          log::add('denonavr', 'debug', "<= true");
          return true;
				}				
			}			
		}      
    log::add('denonavr', 'debug', "<= false");
    return false;
  }
	
	/*     * **********************Getteur Setteur*************************** */
}

class denonavrCmd extends cmd {
	/*     * *************************Attributs****************************** */
	
	/*     * ***********************Methode static*************************** */
	
	/*     * *********************Methode d'instance************************* */
	
	public function execute($_options = array()) {
    log::add('denonavr', 'debug', "execute()");
		
    $eqLogic = $this->getEqLogic();    
    $logicalId=$this->getLogicalId();
    $eqType=$this->getConfiguration('eqType');
    if ($eqType=="") {
      log::add('denonavr','warning','Please recreate commands....');
      return true;
    }
    log::add('denonavr','debug',' - eqType: ' . $eqType . ', command: ' . $logicalId);
    if ($logicalId == "refresh") {
      $eqLogic->updateInfo();
      return true;
    }    
    
		if ($eqLogic->getConfiguration('mode') == 'H') {
      if (! $eqLogic -> isLive()) {
        log::add('denonavr','debug',' - isLive: false. Abording');
        return true;
      }   
      $baseUrl='http://' . $eqLogic->getConfiguration('ip') . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/formiPhoneAppDirect.xml?';        
      log::add('denonavr', 'debug', " - baseURL: " . $baseUrl);
      if ($eqType =="power") {
		    if ($logicalId == 'on') {
		      $request_http = new com_http($baseUrl . 'ZMON');
		    } elseif ($logicalId == 'off') {
		        $request_http = new com_http($baseUrl . 'ZMOFF');
          }
      } elseif ($eqType == "volume") {
		      if ($logicalId == 'volume_set') {
            //converting to absolute
            $volume = $_options['slider'] + config::byKey('absolute_volume_offset', 'denonavr');
            if ($volume<10) $volume = '0' . $volume;
              else $volume = '' . $volume;  
            if ($eqLogic->getConfiguration('zone', 'main') != 'main') $zone = 'Z' . $eqLogic->getConfiguration('zone', 'main');
              else $zone = 'MV';              
		        $request_http = new com_http($baseUrl . $zone . $volume);
		      } elseif ($logicalId == 'mute') {
              //stateString = 'Z' + this.zone + 'MU' + (state ? 'ON' : 'OFF');
              if ($eqLogic->getConfiguration('zone', 'main') != 'main') $zone = 'Z' . $eqLogic->getConfiguration('zone', 'main');
		            else $zone = '';              
              $infos=false;
              try {
                $infos = $eqLogic -> getAmpInfoLightHEOS();
              } catch (Exception $e) {
                  log::add('denonavr', 'warning', " - cannot get current Status.");
                }                  
              if (is_array($infos) && isset($infos['Mute'])) {
                if ($infos['Mute'] == "off" || $infos['Mute'] == "OFF") $url = $baseUrl . $zone . "MUON";
                  else $url = $baseUrl . $zone . "MUOFF";
              } else $url = $baseUrl . $zone . "MUON";
			        $request_http = new com_http($url);
			      }
        } elseif ($eqType == "input") { // input 
            log::add('denonavr', 'debug', " - SELECT INPUT: " . $logicalId);
            $baseUrl='http://' . $eqLogic->getConfiguration('ip') . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/formiPhoneAppDirect.xml?'; 
            if ($eqLogic->getConfiguration('zone', 'main') != 'main') $zone = 'Z' . $eqLogic->getConfiguration('zone', 'main');
		          else $zone = 'SI';              
            $url = $baseUrl . $zone . $logicalId; 
            $request_http = new com_http($url);
          } else {
              log::add('denonavr','warning','Category is unknown....');
              return true;
            }
      log::add('denonavr', 'debug', " - url: " . $request_http->getUrl());
      $request_http->exec(60);
		} elseif ($eqLogic->getConfiguration('mode') == '') {
      $zone = '';
		  if ($eqLogic->getConfiguration('zone', 'main') == 2) {
			  $zone = '&ZoneName=ZONE2';
		  }      
      $baseUrl='http://' . $eqLogic->getConfiguration('ip') . ':' . config::byKey('apiport_standard', 'denonavr') . '/MainZone/index.put.asp?';
      log::add('denonavr', 'debug', " - baseURL: " . $baseUrl);
			if ($logicalId == 'on') {
				$request_http = new com_http($baseUrl . 'cmd0=PutZone_OnOff%2FON' . $zone);
			} elseif ($logicalId == 'off') {
				  $request_http = new com_http($baseUrl . 'cmd0=PutZone_OnOff%2FOFF' . $zone);
			  } elseif ($logicalId == 'volume_set') {
				    $request_http = new com_http($baseUrl . '?cmd0=PutMasterVolumeSet%2F' . $_options['slider'] . $zone);
			    } elseif ($logicalId == 'mute') {
				      $request_http = new com_http($baseUrl . 'cmd0=PutVolumeMute/TOGGLE');
			      } else { // input 
				        $request_http = new com_http($baseUrl . 'cmd0=PutZone_InputFunction%2F' . $logicalId . $zone);
		        	}
			//$request_http->exec(60);
		}
    
		sleep(1);
		$eqLogic->updateInfo();
    return true;
	}
	
	/*     * **********************Getteur Setteur*************************** */
}

?>

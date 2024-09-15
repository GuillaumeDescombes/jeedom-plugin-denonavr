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

  public static function deamon_info() {
    $return = array();
    $return['log'] = 'denonavrd';
    $return['state'] = 'nok';
    $pid_file = jeedom::getTmpFolder('denonavr') . '/deamon.pid';
    if (file_exists($pid_file)) {
      if (@posix_getsid(trim(file_get_contents($pid_file)))) {
        $return['state'] = 'ok';
      } else {
        shell_exec(system::getCmdSudo() . 'rm -rf ' . $pid_file . ' 2>&1 > /dev/null');
      }
    }
    $return['launchable'] = 'ok';
    return $return;
  }
  
  public static function dependancy_info() {
    $return = array();
    $return['log'] = 'denonavr_update';
    $return['progress_file'] = jeedom::getTmpFolder('denonavr') . '/dependance';
    $return['state'] = (self::compilationOk()) ? 'ok' : 'nok';
    return $return;
  }
  public static function dependancy_install() {
    log::remove('denonavr_update');
    return array('script' => __DIR__ . '/../../resources/install_#stype#.sh ' . jeedom::getTmpFolder('denonavr') . '/dependance', 'log' => log::getPathToLog('denonavr_update'));
  }
  
  public static function compilationOk() {
    if (exec(system::getCmdSudo() . system::get('cmd_check') . '-E "python3\-request|python3\-pyudev" | wc -l') <2) {
      return false;
    }      
    return true;
  }  
  
  public static function deamon_start() {
    self::deamon_stop();
    $deamon_info = self::deamon_info();
    if ($deamon_info['launchable'] != 'ok') {
      throw new Exception(__('Veuillez vérifier la configuration', __FILE__));
    }

    $demonavr_path = realpath(__DIR__ . '/../../resources/avrd');
    $cmd = '/usr/bin/python3 ' . $demonavr_path . '/avrd.py';
    $cmd .= ' --loglevel ' . log::convertLogLevel(log::getLogLevel('denonavr'));
    $cmd .= ' --socketport ' . config::byKey('socketport', 'denonavr');
    $cmd .= ' --cycle ' . config::byKey('cycle', 'denonavr');
    $cmd .= ' --callback ' . network::getNetworkAccess('internal', 'proto:127.0.0.1:port:comp') . '/plugins/denonavr/core/php/jeeDenonAVR.php';
    $cmd .= ' --apikey ' . jeedom::getApiKey('denonavr');
    $cmd .= ' --pid ' . jeedom::getTmpFolder('denonavr') . '/deamon.pid';
    log::add('denonavr', 'info', 'Lancement démon denonavr : ' . $cmd);
    $result = exec($cmd . ' >> ' . log::getPathToLog('denonavrd') . ' 2>&1 &');
    $i = 0;
    while ($i < 30) {
      $deamon_info = self::deamon_info();
      if ($deamon_info['state'] == 'ok') {
        break;
      }
      sleep(1);
      $i++;
    }
    if ($i >= 30) {
      log::add('denonavr', 'error', 'Impossible de lancer le démon denonavr, vérifiez le port', 'unableStartDeamon');
      return false;
    }
    message::removeAll('denonavr', 'unableStartDeamon');
    return true;
  }
  
  public static function deamon_stop() {
    $pid_file = jeedom::getTmpFolder('denonavr') . '/deamon.pid';
    if (file_exists($pid_file)) {
      $pid = intval(trim(file_get_contents($pid_file)));
      system::kill($pid);
    }
    system::kill('avrd.py');
    system::fuserk(config::byKey('socketport', 'denonavr'));
    sleep(1);
  }  
  
  public static function request($_action, $_data = null) {
    $paramDefault = array('apikey' => jeedom::getApiKey('denonavr'));
    if ($_data == null) $_data=array();
    
    $value = json_encode(array_merge($paramDefault, array('action' => $_action), $_data));
    $socket = socket_create(AF_INET, SOCK_STREAM, 0);
    socket_connect($socket, '127.0.0.1', config::byKey('socketport', 'denonavr'));
    socket_write($socket, $value, strlen($value));
    socket_close($socket);
    
    log::add('denonavr', 'debug', "Call deamon: ". $value);
    return true;
  }
    

  /*
  public static function cron() {
  }
  */

  /*     
  public static function cron5() {
  }
  */
  public static function cron15() {
    foreach (eqLogic::byType('denonavr', true) as $eqLogic) {
      if ($eqLogic->getConfiguration('enableDaemon') == 0) {
        $eqLogic->updateInfo();
      }
    }
  }

  /*
  public static function cronHourly() {
  }
  */

  /*
  public static function cronDaily() {
  }  
  */
  
  static public function _getAmpInfoAllHEOS($ip, $zone) {
    log::add('denonavr', 'debug', 'getAmpInfoAllHEOS()');
    
    $url = 'http://' . $ip . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/Deviceinfo.xml';
    $request_http = new com_http($url);
    $result="";
    try {
      $result = trim($request_http->exec(config::byKey('timeout', 'denonavr'), 1));
    } catch (Exception $e) {
        $result='';
      }
    $data=false;
    if (strpos($result, "Error 403") === false) {
      $xml = simplexml_load_string($result);
      $data = json_decode(json_encode($xml), true);
      if (is_array($data)) {
        foreach ($data as $key => $value) {
          if (isset($value['value'])) {
            $data[$key] = $value['value'];
          }
        }
      }
    } else {
        log::add('denonavr', 'debug', " - error 403");
      }

    $jsonString = json_encode($data);
    log::add('denonavr', 'debug', " - data: " . $jsonString);

    return $data;
  }
  
  static public function _getAmpInfo($ip, $zone) {
    log::add('denonavr', 'debug', 'getAmpInfo()');
     
    if ($zone == 2) {
      $zoneHtml = '?ZoneName=ZONE2';
    } elseif ($zone == 3) {
        $zoneHtml = '?ZoneName=ZONE3';
      } else $zoneHtml ='';
      
    $url = 'http://' . $ip . ':' . config::byKey('apiport_standard', 'denonavr') . '/goform/formMainZone_MainZoneXml.xml' . $zoneHtml;
    $request_http = new com_http($url);
    $result="";
    try {
      $result = trim($request_http->exec(config::byKey('timeout', 'denonavr'), 1));
    } catch (Exception $e) {
        $result='';
      }
    $data=false;
    if (strpos($result, "Error 403") === false) { 
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
        log::add('denonavr', 'debug', " - error 403");
      }

    $jsonString = json_encode($data);
    log::add('denonavr', 'debug', " - data: " . $jsonString);

    return $data;
  }
  
  static public function _getAmpInfoLightHEOS($ip, $zone) {
    log::add('denonavr', 'debug', 'getAmpInfoLightHEOS()');
          
    $url = 'http://' . $ip . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/';
    
    if ($zone == 2) $url .= 'formZone2_Zone2XmlStatusLite.xml';
      elseif ($zone == 3) $url .= 'formZone2_Zone3XmlStatusLite.xml'; 
        else $url .= 'formMainZone_MainZoneXmlStatusLite.xml';
        
    $request_http = new com_http($url);
    $result="";
    try {
      $result = trim($request_http->exec(config::byKey('timeout', 'denonavr'), 1));
    } catch (Exception $e) {
        $result='';
      }
    $data=false;
    if (strpos($result, "Error 403") === false) {
      $xml = simplexml_load_string($result);
      $data = json_decode(json_encode($xml), true);
      if (is_array($data)) {
        foreach ($data as $key => $value) {
          if (isset($value['value'])) {
            $data[$key] = $value['value'];
          }
        }
      }
    } else {
        log::add('denonavr', 'debug', " - error 403");
      }
    
    $jsonString = json_encode($data);
    log::add('denonavr', 'debug', " - data: " . $jsonString);

    return $data;
  }
  
  static public function _getAmpInfoHEOS($settings = "all", $ip, $zone) {
    log::add('denonavr', 'debug', 'getAmpInfoHEOS()');
    $AllInfoHEOS = array ("GetZoneName", "GetAllZonePowerStatus", "GetAllZoneSource", "GetAllZoneVolume", "GetAllZoneMuteStatus",
                      "GetRenameSource", "GetDeletedSource", "GetSurroundModeStatus", "GetToneControl", "GetSourceStatus",
                      "GetNetAudioStatus");
    if ($settings == "all") $settings = $AllInfoHEOS;
      elseif (!is_array($settings)) $settings= array($settings);
      
    $url = 'http://' . $ip . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/AppCommand.xml';
    
    $resultXMLs=false;
        
    foreach ($settings as $key => $value) {
      $postData = '<?xml version="1.0" encoding="utf-8"?>\n<tx>\n<cmd id="1">' . $value . '</cmd>\n</tx>';
    
      $request_http = new com_http($url);
      $request_http -> setPost($postData);
      $result="";
      try {
        $result = trim($request_http->exec(config::byKey('timeout', 'denonavr'), 1));
      } catch (Exception $e) {
          $result='';
          break;
        }
      if (strpos($result, "Error 403") === false) {
        $xml = simplexml_load_string($result);
        $resultXMLs[$value]=$xml -> cmd;
      } else {
          log::add('denonavr', 'debug', " - error 403");
          break;
      }
    }
    
    $jsonString = json_encode($resultXMLs);
    log::add('denonavr', 'debug', " - json: " . $jsonString);
    $data=json_decode($jsonString, true);
    return $data;
  } 
    
  static public function volumeAbsolutetoRelative($volumeAbs) {
    return floatval($volumeAbs)-config::byKey('absolute_volume_offset', 'denonavr');
  }
  
  static public function volumeRelativetoAbsolute($volumeRel) {
    return floatval($volumeRel)+config::byKey('absolute_volume_offset', 'denonavr');
  }
  
  
  /*     * *********************Méthodes d'instance************************* */
  
  /*
  public function preInsert() {
    //$this->setCategory('multimedia', 1);
  }
  */

  /*  
  public function postInsert() {
        
  }
  */  
  
  public function preUpdate() {
    if ($this->getConfiguration('ip') == '') {
      throw new Exception(__('Le champs IP ne peut etre vide', __FILE__));
    }
  }
  
  /*
  public function postUpdate() {
        
  }
  */

  /*  
  public function preRemove() {
        
  }
  */

  /*
  public function postRemove() {
        
  } 
  */

  /*
  public function preSave() {
        
  }
  */  
  
  public function postSave() {
    //IP Change -> recreate commands
    if ($this->getConfiguration('applyIP') != $this->getConfiguration('ip')) {
      $this->applyModuleConfiguration();
    }
    
    // deamon
    if ($this->getConfiguration('enableDaemon') == 1) {
      $serial=strtolower($this->getConfiguration('serial'));
      if ($this->getConfiguration('applySerial') != $serial) {        
        log::add('denonavr', 'info', 'update of serial: from ' . $this->getConfiguration('applySerial') . ' to '.$serial);
        //unregister old serial
        if ($this->getConfiguration('applySerial') !='') {
          log::add('denonavr', 'info', "Unregister serial #" . $this->getConfiguration('applySerial') ." in deamon");
          self::request('unregister', array("serial" => $this->getConfiguration('applySerial')));
        }

        //register new serial
        log::add('denonavr', 'info', "register serial #" . $serial ." in deamon");
        $ip = $this->getConfiguration('ip');
        $name = "Device #" . $serial;        
        self::request('register', array('serial' => $serial, 'ip' => $ip, 'name' => $name));
        
        $this->setConfiguration('applySerial', $serial);
        if ($this->getConfiguration('serial') != $serial) $this->setConfiguration('serial', $serial);
        $this->save();        
      }
    } else {
        if ($this->getConfiguration('applySerial') != '') { 
          $serial=strtolower($this->getConfiguration('serial'));
          //unregister serial
          log::add('denonavr', 'info', "Unregister serial #" . $serial ." in deamon");
          self::request('unregister', array("serial" => $serial));
          
          $this->setConfiguration('applySerial', '');
          $this->save();
        }
      }
  }

  public function applyModuleConfiguration() {
    log::add('denonavr', 'info', 'applyModuleConfiguration()');
    $this->setConfiguration('applyIP', $this->getConfiguration('ip'));
    $this->save();
    
    $zone=$this->getConfiguration('zone', 'main');
    $order=1;
    
    //REFRESH
    $cmd = $this->getCmd(null, 'refresh');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'refresh'");      
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('refresh');
    }
    $cmd->setName(__('Rafraîchir', __FILE__));
    $cmd->setIsVisible(1);    
    $cmd->setType('action');
    $cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "other");
    $cmd->setEqLogic_id($this->getId());
    $cmd->setOrder($order++);
    $cmd->save();    
    
    //POWER
    $cmd = $this->getCmd(null, 'power_state');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'power_state'");
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('power_state');
    }
    $cmd->setIsVisible(0);
    $cmd->setName(__('Etat', __FILE__));
    $cmd->setType('info');
    $cmd->setSubType('binary');
    $cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "power");
    $cmd->setDisplay('generic_type', 'MEDIA_STATE');
    $cmd->setOrder($order++);
    $cmd->save();
    $power_state_id = $cmd->getId();

    $cmd = $this->getCmd(null, 'on');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'on'");      
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('on');
    }
    $cmd->setName(__('On', __FILE__));    
    $cmd->setIsVisible(1);
    $cmd->setTemplate('dashboard', 'prise');
    $cmd->setTemplate('mobile', 'prise');    
    $cmd->setType('action');
    $cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "power");
    $cmd->setEqLogic_id($this->getId());
    $cmd->setDisplay('generic_type', 'MEDIA_ON');
    $cmd->setValue($power_state_id);
    $cmd->setOrder($order++);
    $cmd->save();
    
    $cmd = $this->getCmd(null, 'off');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'off'");      
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('off');
    }
    $cmd->setName(__('Off', __FILE__));
    $cmd->setIsVisible(1);
    $cmd->setTemplate('dashboard', 'prise');
    $cmd->setTemplate('mobile', 'prise');    
    $cmd->setType('action');
    $cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "power");
    $cmd->setEqLogic_id($this->getId());
    $cmd->setDisplay('generic_type', 'MEDIA_OFF');
    $cmd->setValue($power_state_id);
    $cmd->setOrder($order++);
    $cmd->save();    
    
    // MUTE
    $cmd = $this->getCmd(null, 'mute_state');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'mute_state'");
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('mute_state');
    }
    $cmd->setIsVisible(0);
    $cmd->setName(__('Muet', __FILE__));
    $cmd->setType('info');
    $cmd->setSubType('binary');
    $cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "volume");
    $cmd->setDisplay('generic_type', 'MEDIA_STATE');
    $cmd->setOrder($order++);
    $cmd->save();
    $mute_state_id = $cmd->getId();    
    
    $cmd = $this->getCmd(null, 'mute_on');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'mute_on'");      
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('mute_on');   
    }
    $cmd->setName(__('Muet On', __FILE__));
    $cmd->setIsVisible(1);
    $cmd->setTemplate('dashboard', 'circle');
    $cmd->setTemplate('mobile', 'circle');       
    $cmd->setType('action');
    $cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "volume");
    $cmd->setEqLogic_id($this->getId());
    $cmd->setDisplay('generic_type', 'MEDIA_MUTE');
    $cmd->setValue($mute_state_id);
    $cmd->setOrder($order++);
    $cmd->save();
    
    $cmd = $this->getCmd(null, 'mute_off');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'mute_off'");      
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('mute_off'); 
    }
    $cmd->setName(__('Muet Off', __FILE__));
    $cmd->setIsVisible(1);
    $cmd->setTemplate('dashboard', 'circle');
    $cmd->setTemplate('mobile', 'circle');         
    $cmd->setType('action');
    $cmd->setSubType('other');
    $cmd->setConfiguration('eqType', "volume");
    $cmd->setEqLogic_id($this->getId());
    $cmd->setDisplay('generic_type', 'MEDIA_UNMUTE');
    $cmd->setValue($mute_state_id);
    $cmd->setOrder($order++);
    $cmd->save();  
    
    //VOLUME
    $cmd = $this->getCmd(null, 'volume');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'volume'");      
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('volume');
    }
    $cmd->setIsVisible(0);
    $cmd->setName(__('Valeur Volume', __FILE__));
    $cmd->setType('info');
    $cmd->setSubType('numeric');
    $cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "volume");
    $cmd->setUnite('%');
    $cmd->setDisplay('generic_type', 'VOLUME');
    $cmd->setOrder($order++);
    $cmd->save();
    $volume_id = $cmd->getId();    
    
    $cmd = $this->getCmd(null, 'volume_set');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'volume_set'");      
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('volume_set');

    }
    $cmd->setName(__('Niveau Volume', __FILE__));
    $cmd->setIsVisible(1);
    $cmd->setType('action');
    $cmd->setSubType('slider');
    $cmd->setConfiguration('minValue', config::byKey('min_volume', 'denonavr'));
    $cmd->setConfiguration('maxValue', config::byKey('max_volume', 'denonavr'));
    $cmd->setConfiguration('eqType', "volume");
    $cmd->setDisplay('generic_type', 'SET_VOLUME');
    $cmd->setValue($volume_id);
    $cmd->setEqLogic_id($this->getId());
    $cmd->setOrder($order++);
    $cmd->save();
    
    
    $cmd = $this->getCmd(null, 'input');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'input'");
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('input');
    }
    $cmd->setIsVisible((config::byKey('source_action', 'denonavr') == 'select' ? 0:1));
    $cmd->setName(__('Valeur Source', __FILE__));
    $cmd->setType('info');
    $cmd->setSubType('string');
    $cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "input");
    $cmd->setDisplay('generic_type', 'GENERIC');
    $cmd->setOrder($order++);
    $cmd->save();
    $input_id = $cmd->getId();     
    
    //INPUT
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
        $model='1';
        try {
          $infos = $this->getAmpInfo();
          $model = $infos['ModelId'];
        } catch (Exception $e) {
          }  
        if (isset($convert[$model])) {
          $model = $convert[$model];
        }
        if (isset($inputModel[$model])) {
          $inputNames = $inputModel[$model];
          if ($zone!="main") $inputNames["SOURCE"] = "Source Principale";
          $this->setConfiguration('inputNames', $inputNames);
          foreach ($inputNames as $key => $value) {
            $cmd = $this->getCmd(null, $key);
            if (!is_object($cmd)) {
              log::add('denonavr', 'info', " - creating '" . $key . "'");
              $cmd = new denonavrCmd();
              $cmd->setLogicalId($key);
            }
            $cmd->setName(__($value, __FILE__));
            $cmd->setIsVisible(1);            
            $cmd->setType('action');
            $cmd->setSubType('other');
            $cmd->setConfiguration('eqType', "input");
            $cmd->setEqLogic_id($this->getId());
            $cmd->setOrder($order++);
            $cmd->save();
          }
        } else {
          $this->setConfiguration('inputNames', array());
        }
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
            $inputNames=array();
            $inputSelectMapping='';
            if ($zone!="main") $infos['GetRenameSource']['functionrename']['list'][] = array("name" => "SOURCE", "rename" => "Source Principale");
            foreach ($infos['GetRenameSource']['functionrename']['list'] as $list) {
              $inuse = "1";
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
              $inputNames[$inputID]=$inputRenamed;
              $cmd = $this->getCmd(null, $inputID);
              if (config::byKey('source_action', 'denonavr') == 'button') {
                if (!is_object($cmd)) {
                  log::add('denonavr', 'info', " - creating '" . $list['name'] . "'");
                  $cmd = new denonavrCmd();
                  $cmd->setLogicalId($inputID);
                }
                $cmd->setName(__($inputRenamed, __FILE__));                
                $cmd->setIsVisible($inuse=="1"?1:0);
                $cmd->setType('action');
                $cmd->setSubType('other');
                $cmd->setConfiguration('eqType', "input");
                $cmd->setEqLogic_id($this->getId());
                $cmd->setOrder($order++);
                $cmd->save();                
              } else { //deleting command if exists
                if (is_object($cmd)) $cmd->remove();
                log::add('denonavr', 'info', " - removing $inputID");
                if ($inuse) $inputSelectMapping.=$inputID."|".$inputRenamed.";";
              }
            }
            $inputSelectMapping=substr($inputSelectMapping, 0, -1);
            log::add('denonavr', 'info', "list of inputs: " . print_r($inputNames, true));
            $this->setConfiguration('inputNames', $inputNames);
            $cmd = $this->getCmd(null, "input_set");
            if (config::byKey('source_action', 'denonavr') == 'select'){
              if (!is_object($cmd)) {
                log::add('denonavr', 'info', " - creating input_set");
                $cmd = new denonavrCmd();
                $cmd->setLogicalId("input_set");
              }
              $cmd->setName(__("Source", __FILE__));
              $cmd->setIsVisible(1);
              $cmd->setType('action');
              $cmd->setSubType('select');
              $cmd->setConfiguration('eqType', "input");
              $cmd->setConfiguration('listValue',$inputSelectMapping);
              $cmd->setEqLogic_id($this->getId());
              $cmd->setValue($input_id);
              $cmd->setOrder($order++);
              $cmd->save();                
            } else {
              if (is_object($cmd)) $cmd->remove();
              log::add('denonavr', 'info', " - removing input_set");
            }
          }    
        }
    }
    
    //SURROUND
    $cmd = $this->getCmd(null, 'surround');
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating 'surround'");
      $cmd = new denonavrCmd();
      $cmd->setLogicalId('surround');
    }
    $cmd->setIsVisible(0);
    $cmd->setName(__('Valeur Surround', __FILE__));
    $cmd->setType('info');
    $cmd->setSubType('string');
    $cmd->setEqLogic_id($this->getId());
    $cmd->setConfiguration('eqType', "sound");
    $cmd->setDisplay('generic_type', 'GENERIC');
    $cmd->setOrder($order++);
    $cmd->save();
    $surround_id = $cmd->getId();
    
    $surroundNames=array(
      "MOVIE" => "Film",
      "MUSIC" => "Musique",
      "GAME" => "Jeux vidéo",
      "DIRECT" => "Direct",
      "PURE DIRECT" => "Direct (pure)",
      "STEREO" => "Stereo",
      "AUTO" => "Auto",
      "DOLBY DIGITAL" => "Dolby Digital",
      "DTS SURROUND" => "DTS",
      "MCH STEREO" => "Stereo (Multi Chan)",
      "SUPER STADIUM" => "Stade",
      "ROCK ARENA" => "Rock Arena",
      "JAZZ CLUB" => "Jazz Club",
      "CLASSIC CONCERT" => "Concert classique",
      "MONO MOVIE" => "Film (Mono)",
      "MATRIX" => "Matrix",
      "VIRTUAL" => "Virtual"
    );
    $this->setConfiguration('surroundNames', $surroundNames);
    $surroundSelectMapping="";
    foreach ($surroundNames as $key => $value) {
      $surroundSelectMapping.=$key."|".$value.";";
    }
    $surroundSelectMapping=substr($surroundSelectMapping, 0, -1);
    
    $cmd = $this->getCmd(null, "surround_set");
    if (!is_object($cmd)) {
      log::add('denonavr', 'info', " - creating surround_set");
      $cmd = new denonavrCmd();
      $cmd->setLogicalId("surround_set");
    }
    $cmd->setName(__("Surround", __FILE__));
    $cmd->setIsVisible(1);
    $cmd->setType('action');
    $cmd->setSubType('select');
    $cmd->setConfiguration('eqType', "sound");
    $cmd->setConfiguration('listValue', $surroundSelectMapping);
    $cmd->setEqLogic_id($this->getId());
    $cmd->setValue($surround_id);
    $cmd->setOrder($order++);
    $cmd->save();        
    
    if ($this->getConfiguration('zone', 'main')=="main") {
      //RADIO PRESET
      $cmd = $this->getCmd(null, 'preset');
      if (!is_object($cmd)) {
        log::add('denonavr', 'info', " - creating 'preset'");      
        $cmd = new denonavrCmd();
        $cmd->setLogicalId('preset');
      }
      $cmd->setIsVisible(0);
      $cmd->setName(__('Valeur Présélection', __FILE__));
      $cmd->setType('info');
      $cmd->setSubType('numeric');
      $cmd->setEqLogic_id($this->getId());
      $cmd->setConfiguration('eqType', "tuner");
      $cmd->setUnite('');
      $cmd->setDisplay('generic_type', 'CHANNEL');
      $cmd->setOrder($order++);
      $cmd->save();
      $preset_id = $cmd->getId();    
    
      $cmd = $this->getCmd(null, 'preset_set');
      if (!is_object($cmd)) {
        log::add('denonavr', 'info', " - creating 'preset_set'");      
        $cmd = new denonavrCmd();
        $cmd->setLogicalId('preset_set');
      }
      $cmd->setName(__('Présélection Radio', __FILE__));
      $cmd->setIsVisible(1);
      $cmd->setType('action');
      $cmd->setSubType('slider');
      $cmd->setConfiguration('minValue', 1);
      $cmd->setConfiguration('maxValue', 56);
      $cmd->setTemplate('dashboard', 'value');
      $cmd->setTemplate('mobile', 'value');         
      $cmd->setConfiguration('eqType', "tuner");
      $cmd->setDisplay('generic_type', 'SET_CHANNEL');
      $cmd->setValue($preset_id);
      $cmd->setEqLogic_id($this->getId());
      $cmd->setOrder($order++);
      $cmd->save();    
    
      //STATION NAME
      $cmd = $this->getCmd(null, 'station_name');
      if (!is_object($cmd)) {
        log::add('denonavr', 'info', " - creating 'station_name'");      
        $cmd = new denonavrCmd();
        $cmd->setLogicalId('station_name'); 
      }
      $cmd->setName(__('Nom de Station', __FILE__));
      $cmd->setIsVisible(1);
      $cmd->setTemplate('dashboard', 'tile');
      $cmd->setTemplate('mobile', 'tile');         
      $cmd->setType('info');
      $cmd->setSubType('string');
      $cmd->setConfiguration('eqType', "tuner");
      $cmd->setEqLogic_id($this->getId());
      $cmd->setDisplay('generic_type', 'MEDIA_TITLE');
      $cmd->setOrder($order++);
      $cmd->save();      
    }
    
    $this->updateInfo();
  }

  public function getAmpInfo() {
    return denonavr::_getAmpInfo($this->getConfiguration('ip'), $this->getConfiguration('zone', 'main'));
  }
  
  public function getAmpInfoAllHEOS() {
    return denonavr::_getAmpInfoAllHEOS($this->getConfiguration('ip'), $this->getConfiguration('zone', 'main'));
  }

  public function getAmpInfoLightHEOS() {
    return denonavr::_getAmpInfoLightHEOS($this->getConfiguration('ip'), $this->getConfiguration('zone', 'main'));
  }

  public function getAmpInfoHEOS($settings = "all") {
    return denonavr::_getAmpInfoHEOS($settings, $this->getConfiguration('ip'), $this->getConfiguration('zone', 'main'));
  }
  
  public function updateInfo() {
    log::add('denonavr', 'debug', "updateInfo()");
    if ($this->getConfiguration('ip') == '') {
      return;
    }
    
    if ($this->getConfiguration('mode') == '') {
      $infos = $this->getAmpInfo();
      if (isset($infos['ZonePower'])) {
        $this->checkAndUpdateCmd('power_state', ($infos['ZonePower'] == 'OFF') ? 0 : 1);
      } else $this->checkAndUpdateCmd('power_state', 0);
      if (isset($infos['InputFuncSelect'])) {
        $this->checkAndUpdateCmd('input', $infos['InputFuncSelect']);
      }
      if (isset($infos['MasterVolume'])) {
        $this->checkAndUpdateCmd('volume', $infos['MasterVolume']);
      }
      if (isset($infos['selectSurround'])) {
        $this->checkAndUpdateCmd('surround', $infos['selectSurround']);
      }
    } elseif ($this->getConfiguration('mode') == 'H') {
        $infos = $this->getAmpInfoLightHEOS();
        if (isset($infos['Power'])) {
          $this->checkAndUpdateCmd('power_state', ($infos['Power'] == 'OFF') ? 0 : 1);
        } else $this->checkAndUpdateCmd('power_state', 0);
        if (isset($infos['InputFuncSelect'])) {
          $this->checkAndUpdateCmd('input', $infos['InputFuncSelect']);
        }
        if (isset($infos['MasterVolume'])) {
          $volume = $infos['MasterVolume'];
          $this->checkAndUpdateCmd('volume', $volume);
        }
        $infos = $this->getAmpInfoHEOS("GetSurroundModeStatus");
        if (isset($infos['GetSurroundModeStatus']['surround'])) {
          $this->checkAndUpdateCmd('surround', trim($infos['GetSurroundModeStatus']['surround']));
        }
        $infos = $this->getAmpInfoAllHEOS();
        log::add('denonavr', 'info', "AmpInfoAllHEOS: ".print_r($infos, true)); 
        
      }
  }

 public function getTunerStationList() {
    $tunerStationList = $this->getConfiguration('tunerStationList', array());
    return $tunerStationList;
 }

 public function setTunerStationList($aList) {
    $this->setConfiguration('tunerStationList', $aList);
 }
  
  
  /*     * **********************Getteur Setteur*************************** */
}

class denonavrCmd extends cmd {
  /*     * *************************Attributs****************************** */
  
  /*     * ***********************Methode static*************************** */

  private static function executeHeosMode($eqLogic, $eqType, $logicalId, $_options) {
    log::add('denonavr', 'info', "executeHeosMode()");
    $baseUrl='http://' . $eqLogic->getConfiguration('ip') . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/formiPhoneAppDirect.xml?';        
    $request_http=null;
    if ($eqType =="power") {
      if ($logicalId == 'on') {
        $request_http = new com_http($baseUrl . 'ZMON');
      }
      if ($logicalId == 'off') {
        $request_http = new com_http($baseUrl . 'ZMOFF');
      }
    } 
    if ($eqType == "volume") {
      if ($logicalId == 'volume_set') {
        //converting to absolute
        $volume = $_options['slider'] + config::byKey('absolute_volume_offset', 'denonavr');
        if ($volume<10) $volume = '0' . $volume;
          else $volume = '' . $volume;  
        if ($eqLogic->getConfiguration('zone', 'main') != 'main') $zone = 'Z' . $eqLogic->getConfiguration('zone', 'main');
          else $zone = 'MV';              
        $request_http = new com_http($baseUrl . $zone . $volume);
      }
      if ($logicalId == 'mute_on') {
        if ($eqLogic->getConfiguration('zone', 'main') != 'main') $zone = 'Z' . $eqLogic->getConfiguration('zone', 'main');
          else $zone = '';                            
        $url = $baseUrl . $zone . "MUON";
        $request_http = new com_http($url);
      }
      if ($logicalId == 'mute_off') {
        if ($eqLogic->getConfiguration('zone', 'main') != 'main') $zone = 'Z' . $eqLogic->getConfiguration('zone', 'main');
          else $zone = '';                            
        $url = $baseUrl . $zone . "MUOFF";
        $request_http = new com_http($url);
      }      
    }
    if ($eqType == "input") { // input 
      if ($logicalId!="input") { // mode button
        log::add('denonavr', 'debug', " - SELECT INPUT: " . $logicalId);
        $baseUrl='http://' . $eqLogic->getConfiguration('ip') . ':' . config::byKey('apiport_heos', 'denonavr') . '/goform/formiPhoneAppDirect.xml?'; 
        if ($eqLogic->getConfiguration('zone', 'main') != 'main') $zone = 'Z' . $eqLogic->getConfiguration('zone', 'main');
          else $zone = 'SI';              
        $url = $baseUrl . $zone . $logicalId; 
        $request_http = new com_http($url);
      } else { // mode SelectBox
          //to do
        }
    }
    if ($request_http!=null) {
      log::add('denonavr', 'debug', " - url: " . $request_http->getUrl());
      $request_http->exec(60);
      return true;
    } else {
        log::add('denonavr', 'info', " - nothing to do!");
        return false;
      }
  }
  
  private static function executeStandardMode($eqLogic, $eqType, $logicalId, $_options) {
    log::add('denonavr', 'info', "executeStandardMode()");
    $zone = '';
    if ($eqLogic->getConfiguration('zone', 'main') == 2) {
     $zone = '&ZoneName=ZONE2';
    }      
    $baseUrl='http://' . $eqLogic->getConfiguration('ip') . ':' . config::byKey('apiport_standard', 'denonavr') . '/MainZone/index.put.asp?';
    log::add('denonavr', 'debug', " - baseURL: " . $baseUrl);
    
    $request_http=null;
    if ($logicalId == 'on') {
      $request_http = new com_http($baseUrl . 'cmd0=PutZone_OnOff%2FON' . $zone);
    } elseif ($logicalId == 'off') {
        $request_http = new com_http($baseUrl . 'cmd0=PutZone_OnOff%2FOFF' . $zone);
      } elseif ($logicalId == 'volume_set') {
          $request_http = new com_http($baseUrl . '?cmd0=PutMasterVolumeSet%2F' . $_options['slider'] . $zone);
        } elseif ($logicalId == 'mute_on' || $logicalId == 'mute_off') {
            $request_http = new com_http($baseUrl . 'cmd0=PutVolumeMute/TOGGLE');
          } else { // input 
              $request_http = new com_http($baseUrl . 'cmd0=PutZone_InputFunction%2F' . $logicalId . $zone);
             }
    if ($request_http!=null) {
      log::add('denonavr', 'debug', " - url: " . $request_http->getUrl());
      $request_http->exec(60);
      return true;
    } else {
        log::add('denonavr', 'info', " - nothing to do!");
        return false;
      }        
  }
  
  private static function executeDaemon($eqLogic, $eqType, $logicalId, $_options) {
    log::add('denonavr', 'debug', "executeDaemon()");
    $zone = $eqLogic->getConfiguration('zone', 'main');
    $serial = $eqLogic->getConfiguration('serial');
    
    $executed=false;
    if ($eqType == "other") {
      if ($logicalId == 'refresh') {
        log::add('denonavr', 'info', "Request doDevice (Refresh)");
        $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'Refresh'));
        $executed=true;
      }      
    }
    
    if ($eqType == "volume" && !$executed) {
      if ($logicalId == 'mute_on') {
        log::add('denonavr', 'info', "Request doDevice (MuteVolume, $zone, true)");
        $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'MuteVolume', 'zone' => $zone, 'value' => true));
        $executed=true;
      }
      if ($logicalId == 'mute_off') {
        log::add('denonavr', 'info', "Request doDevice (MuteVolume, $zone, false)");
        $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'MuteVolume', 'zone' => $zone, 'value' => false));
        $executed=true;
      }
      if ($logicalId == 'volume_set') {
        if (isset($_options['slider'])) $volume=$_options['slider'];
          elseif (isset($_options['select'])) $volume=intval($_options['select']);
        if (isset($volume)) {
          $volume=denonavr::volumeRelativetoAbsolute($volume);
          log::add('denonavr', 'info', "Request doDevice (SetVolume, $zone, $volume)");
          $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'SetVolume', 'zone' => $zone, 'value' => $volume));
        }
        $executed=true;
      }
    }
    if ($eqType == "power" && !$executed) {
      if ($logicalId == 'on') {
        log::add('denonavr', 'info', "Request doDevice (TurnOn/TurnAVROn, $zone)");
        $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TurnOn', 'zone' => $zone));
        //if ($zone != "main") $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TurnOn', 'zone' => $zone));
        //  else $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TurnAVROn'));
        $executed=true;  
      }
      if ($logicalId == 'off') {
        log::add('denonavr', 'info', "Request doDevice (TurnOff/TurnAVROff, $zone)");
        $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TurnOff', 'zone' => $zone));
        //if ($zone != "main") $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TurnOff', 'zone' => $zone));
        //  else $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TurnAVROff'));
        $executed=true;
      }
    }
    if ($eqType == "input" && !$executed) { // input 
      if ($logicalId!="input" && $logicalId!="input_set") { // mode button
        log::add('denonavr', 'info', "Request doDevice (SelectSource, $zone, $logicalId)");
        $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'SelectSource', 'zone' => $zone, 'value' => $logicalId));
        $executed=true;
      }
      if ($logicalId=="input_set") { // mode selectbox
        if (isset($_options['select'])) {
          $input= $_options['select'];
          log::add('denonavr', 'info', "Request doDevice (SelectSource, $zone, $input)");
          $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'SelectSource', 'zone' => $zone, 'value' => $input));
          $executed=true;
        }
      }
    }    
    if ($eqType == "sound" && !$executed) { // sound
      if ($logicalId=="surround_set") { // mode selectbox
        if (isset($_options['select'])) {
          $surround= $_options['select'];
          log::add('denonavr', 'info', "Request doDevice (SelectSoundMode, $zone, $surround)");
          $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'SelectSoundMode', 'zone' => $zone, 'value' => $surround));
          $executed=true;
        }
      }
    }
    if ($eqType == "tuner" && !$executed) { // tuner
      if ($logicalId!="preset" && $logicalId!="preset_set" && $logicalId!="station_name") { // mode button
        $preset=intval(substr($logicalId,strlen("preset_"),2));
         log::add('denonavr', 'info', "Request doDevice (TunerPreset, $preset)");
         $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TunerPreset', 'value' => $preset));
         $executed=true;
      }    
      if ($logicalId=="preset_set") { // mode selectbox or slider
         if (isset($_options['slider'])) $preset=intval($_options['slider']);
           elseif (isset($_options['select'])) $preset=intval($_options['select']);
             else $preset=1; // default
         log::add('denonavr', 'info', "Request doDevice (TunerPreset, $preset)");
         $eqLogic::request('doDevice',array('serial' => $serial, 'deviceAction' => 'TunerPreset', 'value' => $preset));
         $executed=true;
      }
    }    
    if (!$executed) log::add('denonavr', 'info', " - nothing to do!");
    return $executed;
  }
  
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
    
    //Mode w/o deamon
    if ($eqLogic->getConfiguration('enableDaemon') == 0) {
      if ($logicalId == "refresh") {
        $eqLogic->updateInfo();
      }      
      if ($eqLogic->getConfiguration('mode') == 'H') {
        if (self::executeHeosMode($eqLogic, $eqType, $logicalId, $_options)) {
          sleep(1);
          $eqLogic->updateInfo();      
        }
      } elseif ($eqLogic->getConfiguration('mode') == '') {
          if (self::executeStandardMode($eqLogic, $eqType, $logicalId, $_options)) {
            sleep(1);
            $eqLogic->updateInfo();
          }
        }
    }
    
    //Mode with deamon
    if ($eqLogic->getConfiguration('enableDaemon') == 1) {
      if (!self::executeDaemon($eqLogic, $eqType, $logicalId, $_options)) {
        //not executed via daemon - fallback to HeosMode
        if ($logicalId == "refresh") {
          $eqLogic->updateInfo();
        } elseif (self::executeHeosMode($eqLogic, $eqType, $logicalId, $_options)) {
          sleep(1);
          $eqLogic->updateInfo();
        }
      }
    }

    return true;
  }
  
  /*     * **********************Getteur Setteur*************************** */
}

?>

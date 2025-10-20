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

try {
  require_once dirname(__FILE__) . '/../../../../core/php/core.inc.php';
  include_file('core', 'authentification', 'php');

  if (!isConnect('admin')) {
    throw new Exception(__('401 - Accès non autorisé', __FILE__));
  }

  ajax::init();

  if (init('action') == 'getSSDPDescription') {
  include_file('core', 'ssdp', 'class','denonavr');
  //require_once dirname(__FILE__) . '/../php/ssdp.class.php';
  $ip = init('ip');
    if ($ip=='') {
      throw new Exception(__('IP is not correct : ', __FILE__) . init('ip'));
    }
    $description = phpSSDP::getDeviceByIP($ip);
    if (isset($description['friendlyName'])) {
      log::add('denonavr', 'info', "Ajax - getSSDPDescription: " . json_encode($description));
      //Action
      ajax::success($description);
    } else throw new Exception(__("Pas de réponse de l'IP :" . $ip, __FILE__));
  }

  if (init('action') == 'updateInfo') {
    $eqLogic = denonavr::byId(init('id'));
    if (!is_object($eqLogic)) {
      throw new Exception(__('denonavr eqLogic non trouvé : ', __FILE__) . init('id'));
    }
    //Action
    ajax::success();
  }
  
  if (init('action') == 'createCommands') {
    $eqLogic = denonavr::byId(init('id'));
    if (!is_object($eqLogic)) {
      throw new Exception(__('denonavr eqLogic non trouvé : ', __FILE__) . init('id'));
    }
    if (init('removeexistingcommands') == 1) {
      log::add('denonavr', 'info', 'remove all the existing commands...');
      foreach ($eqLogic->getCmd() as $cmd) {
        $cmd->remove();
      }
    }
    $eqLogic->applyModuleConfiguration();
    ajax::success();
  }  

  throw new Exception(__('Aucune méthode correspondante à : ', __FILE__) . init('action'));
  /*     * *********Catch exeption*************** */
} catch (Exception $e) {
  ajax::error(displayException($e), $e->getCode());
}

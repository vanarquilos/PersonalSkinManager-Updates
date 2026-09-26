#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chroma Special Cases Handler
Handles special cases for chromas (Elementalist Lux forms, HOL chromas, etc.)
"""

from typing import List, Dict, Optional
from utils.core.logging import get_logger

log = get_logger()


class ChromaSpecialCases:
    # PSM_FORMS_V2_V1_LOCK
    # Final runtime QA: clickable/manual FormsWheel controls are disabled for
    # these families in V1. Revenant Reign Viego still keeps its native
    # in-game Ctrl+5 behavior when the base skin is selected normally.
    # Champion-select starting-form choices are enabled for V1.
    # Keep this registry empty unless a family must be hidden for a proven regression.
    V1_DISABLED_FORM_FAMILY_IDS = set()

    # PSM_DYNAMIC_FORMS_V2
    # Selecting one of these real base IDs means native mode: PSM clears
    # any manually forced form and leaves the complete dynamic skin active.
    # Dynamic family base IDs. The existing name is retained for compatibility
    # with the selection path, but only Revenant Reign Viego is currently
    # confirmed to preserve its real in-game native form switching.
    DYNAMIC_NATIVE_BASE_IDS = {
        99007: 99,    # Elementalist Lux — base/static with current archive
        21016: 21,    # Gun Goddess Miss Fortune — base/static with current archive
        222060: 222,  # Arcane Fractured Jinx — base/static with current archive
        234043: 234,  # Revenant Reign Viego — confirmed Native (Ctrl+5)
    }

    CONFIRMED_NATIVE_DYNAMIC_BASE_IDS = {234043}

    @staticmethod
    def is_native_dynamic_base(skin_id: int) -> bool:
        try:
            return int(skin_id) in ChromaSpecialCases.DYNAMIC_NATIVE_BASE_IDS
        except (TypeError, ValueError):
            return False

    @staticmethod
    def get_native_dynamic_champion_id(skin_id: int) -> Optional[int]:
        try:
            return ChromaSpecialCases.DYNAMIC_NATIVE_BASE_IDS.get(int(skin_id))
        except (TypeError, ValueError):
            return None

    """Handles special cases for chromas"""
    # PSM_PHASE5_SPECIAL_FORMS_FINAL
    
    @staticmethod
    def get_elementalist_forms() -> List[Dict]:
        """Get Elementalist Lux Forms data structure (equivalent to chromas)"""
        forms = [
            {'id': 99991, 'name': 'Air', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Air.zip'},
            {'id': 99992, 'name': 'Dark', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Dark.zip'},
            {'id': 99993, 'name': 'Ice', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Ice.zip'},
            {'id': 99994, 'name': 'Magma', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Magma.zip'},
            {'id': 99995, 'name': 'Mystic', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Mystic.zip'},
            {'id': 99996, 'name': 'Nature', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Nature.zip'},
            {'id': 99997, 'name': 'Storm', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Storm.zip'},
            {'id': 99998, 'name': 'Water', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Lux Elementalist Water.zip'},
            {'id': 99999, 'name': 'Fire', 'colors': [], 'is_owned': False, 'form_path': 'Lux/Forms/Elementalist Lux Fire.zip'},
        ]
        log.debug(f"[CHROMA] Created {len(forms)} Elementalist Lux Forms with fake IDs (99991-99999)")
        return forms
    
    @staticmethod
    def get_mordekaiser_forms() -> List[Dict]:
        """Get Sahn Uzal Mordekaiser Forms data structure (equivalent to chromas)"""
        forms = [
            {'id': 82998, 'name': 'Form 1', 'colors': [], 'is_owned': False, 'form_path': 'Mordekaiser/Forms/Sahn Uzal Mordekaiser Form 1.zip'},
            {'id': 82999, 'name': 'Form 2', 'colors': [], 'is_owned': False, 'form_path': 'Mordekaiser/Forms/Sahn Uzal Mordekaiser Form 2.zip'},
        ]
        log.debug(f"[CHROMA] Created {len(forms)} Sahn Uzal Mordekaiser Forms with real IDs (82998, 82999)")
        return forms
    
    @staticmethod
    def get_morgana_forms() -> List[Dict]:
        """Get Spirit Blossom Morgana Forms data structure (equivalent to chromas)"""
        forms = [
            {'id': 25999, 'name': 'Form 1', 'colors': [], 'is_owned': False, 'form_path': 'Morgana/Forms/Spirit Blossom Morgana Form 1.zip'},
        ]
        log.debug(f"[CHROMA] Created {len(forms)} Spirit Blossom Morgana Forms with real ID (25999)")
        return forms
    
    @staticmethod
    def get_sett_forms() -> List[Dict]:
        """Get Radiant Sett Forms data structure (equivalent to chromas)"""
        forms = [
            {'id': 875998, 'name': 'Form 2', 'colors': [], 'is_owned': False, 'form_path': 'Sett/Forms/Radiant Sett Form 2.zip'},
            {'id': 875999, 'name': 'Form 3', 'colors': [], 'is_owned': False, 'form_path': 'Sett/Forms/Radiant Sett Form 3.zip'},
        ]
        log.debug(f"[CHROMA] Created {len(forms)} Radiant Sett Forms with real IDs (875998, 875999)")
        return forms
    
    @staticmethod
    def get_seraphine_forms() -> List[Dict]:
        """Get KDA Seraphine Forms data structure (equivalent to chromas)"""
        forms = [
            {'id': 147002, 'name': 'Form 1', 'colors': [], 'is_owned': False, 'form_path': 'Seraphine/Forms/KDA Seraphine Form 1.zip'},
            {'id': 147003, 'name': 'Form 2', 'colors': [], 'is_owned': False, 'form_path': 'Seraphine/Forms/KDA Seraphine Form 2.zip'},
        ]
        log.debug(f"[CHROMA] Created {len(forms)} KDA Seraphine Forms with real IDs (147002, 147003)")
        return forms
    
    @staticmethod
    def get_jinx_forms() -> List[Dict]:
        """Get Arcane Fractured Jinx forms data structure."""
        forms = [
            {'id': 222998, 'name': 'Form 2', 'colors': [], 'is_owned': False, 'form_path': None},
            {'id': 222999, 'name': 'Form 3', 'colors': [], 'is_owned': False, 'form_path': None},
        ]
        log.debug(
            f"[CHROMA] Created {len(forms)} Arcane Fractured Jinx Forms "
            "with real IDs (222998, 222999)"
        )
        return forms

    @staticmethod
    def get_viego_forms() -> List[Dict]:
        """Get Viego Forms data structure (equivalent to chromas)"""
        forms = [
            {'id': 234994, 'name': 'Form 2', 'colors': [], 'is_owned': False, 'form_path': 'Viego/Forms/Viego Form 2.zip'},
            {'id': 234995, 'name': 'Form 3', 'colors': [], 'is_owned': False, 'form_path': 'Viego/Forms/Viego Form 3.zip'},
            {'id': 234996, 'name': 'Form 4', 'colors': [], 'is_owned': False, 'form_path': 'Viego/Forms/Viego Form 4.zip'},
            {'id': 234997, 'name': 'Form 5', 'colors': [], 'is_owned': False, 'form_path': 'Viego/Forms/Viego Form 5.zip'},
            {'id': 234998, 'name': 'Form 6', 'colors': [], 'is_owned': False, 'form_path': 'Viego/Forms/Viego Form 6.zip'},
            {'id': 234999, 'name': 'Form 7', 'colors': [], 'is_owned': False, 'form_path': 'Viego/Forms/Viego Form 7.zip'},
        ]
        log.debug(f"[CHROMA] Created {len(forms)} Viego Forms with real IDs (234994-234999)")
        return forms
    
    @staticmethod
    def get_missfortune_forms() -> List[Dict]:
        """Get Gun Goddess Miss Fortune Forms data structure (equivalent to chromas)"""
        forms = [
            {'id': 21997, 'name': 'Zero Hour', 'colors': [], 'is_owned': False, 'form_path': 'MissFortune/Forms/Gun Goddess Miss Fortune Zero Hour.zip'},
            {'id': 21998, 'name': 'Royal Arms', 'colors': [], 'is_owned': False, 'form_path': 'MissFortune/Forms/Gun Goddess Miss Fortune Royal Arms.zip'},
            {'id': 21999, 'name': 'Starswarm', 'colors': [], 'is_owned': False, 'form_path': 'MissFortune/Forms/Gun Goddess Miss Fortune Starswarm.zip'},
        ]
        log.debug(f"[CHROMA] Created {len(forms)} Gun Goddess Miss Fortune Forms with real IDs (21997-21999)")
        return forms
    
    @staticmethod
    def get_hol_chromas() -> List[Dict]:
        """Get Risen Legend Kai'Sa HOL chroma data structure (equivalent to chromas)"""
        chromas = [
            {'id': 145071, 'skinId': 145070, 'name': 'Immortalized Legend', 'colors': [], 'is_owned': False},
        ]
        log.debug(f"[CHROMA] Created {len(chromas)} Risen Legend Kai'Sa HOL chromas with real skin ID (145071)")
        return chromas
    
    @staticmethod
    def get_ahri_hol_chromas() -> List[Dict]:
        """Get Risen Legend Ahri HOL chroma data structure (equivalent to chromas)"""
        chromas = [
            {'id': 103086, 'skinId': 103085, 'name': 'Immortalized Legend', 'colors': [], 'is_owned': False},
            {'id': 103087, 'skinId': 103085, 'name': 'Form 2', 'colors': [], 'is_owned': False},
        ]
        log.debug(f"[CHROMA] Created {len(chromas)} Risen Legend Ahri HOL chromas with real skin IDs (103086, 103087)")
        return chromas
    
    @staticmethod
    def is_elementalist_form(chroma_id: int) -> bool:
        """Check if chroma_id is an Elementalist Lux form"""
        return 99991 <= chroma_id <= 99999
    
    @staticmethod
    def is_mordekaiser_form(chroma_id: int) -> bool:
        """Check if chroma_id is a Sahn Uzal Mordekaiser form"""
        return chroma_id in (82998, 82999)
    
    @staticmethod
    def is_morgana_form(chroma_id: int) -> bool:
        """Check if chroma_id is a Spirit Blossom Morgana form"""
        return chroma_id == 25999
    
    @staticmethod
    def is_sett_form(chroma_id: int) -> bool:
        """Check if chroma_id is a Radiant Sett form"""
        return chroma_id in (875998, 875999)
    
    @staticmethod
    def is_seraphine_form(chroma_id: int) -> bool:
        """Check if chroma_id is a KDA Seraphine form"""
        return chroma_id in (147002, 147003)
    
    @staticmethod
    def is_jinx_form(chroma_id: int) -> bool:
        """Check if chroma_id is an Arcane Fractured Jinx form."""
        return chroma_id in (222998, 222999)

    @staticmethod
    def is_viego_form(chroma_id: int) -> bool:
        """Check if chroma_id is a Viego form"""
        return chroma_id in (234994, 234995, 234996, 234997, 234998, 234999)
    
    @staticmethod
    def is_missfortune_form(chroma_id: int) -> bool:
        """Check if chroma_id is a Gun Goddess Miss Fortune form"""
        return chroma_id in (21997, 21998, 21999)
    
    @staticmethod
    def is_hol_chroma(chroma_id: int) -> bool:
        """Check if chroma_id is a HOL chroma"""
        return chroma_id in (145071, 103086, 103087)
    
    @staticmethod
    def get_chromas_for_special_skin(skin_id: int) -> Optional[List[Dict]]:
        # PSM_FORMS_V2_V1_LOCK
        # Do not expose broken clickable/manual FormsWheel controls in V1.
        try:
            if int(skin_id) in ChromaSpecialCases.V1_DISABLED_FORM_FAMILY_IDS:
                return None
        except (TypeError, ValueError):
            pass
        """Get chromas for special skins (Elementalist Lux, HOL chromas, Sahn Uzal Mordekaiser)
        
        Returns:
            List of chroma dicts or None if not a special skin
        """
        # Special case: Elementalist Lux (skin ID 99007) has Forms instead of chromas
        if skin_id == 99007:
            return ChromaSpecialCases.get_elementalist_forms()
        
        # Special case: Sahn Uzal Mordekaiser (skin ID 82054) has Forms instead of chromas
        elif skin_id == 82054:
            return ChromaSpecialCases.get_mordekaiser_forms()
        
        # Special case: Spirit Blossom Morgana (skin ID 25080) has Forms instead of chromas
        elif skin_id == 25080:
            return ChromaSpecialCases.get_morgana_forms()
        
        # Special case: Radiant Sett (skin ID 875066) has Forms instead of chromas
        elif skin_id == 875066:
            return ChromaSpecialCases.get_sett_forms()
        
        # Special case: Radiant Sett forms (IDs 875998, 875999) are treated as forms of base skin
        elif skin_id in (875998, 875999):
            return ChromaSpecialCases.get_sett_forms()
        
        # Special case: KDA Seraphine (skin ID 147001) has Forms instead of chromas
        elif skin_id == 147001:
            return ChromaSpecialCases.get_seraphine_forms()
        
        # Special case: KDA Seraphine forms (IDs 147002, 147003) are treated as forms of base skin
        elif skin_id in (147002, 147003):
            return ChromaSpecialCases.get_seraphine_forms()
        
        # Special case: Arcane Fractured Jinx (skin ID 222060) has Forms.
        elif skin_id == 222060:
            return ChromaSpecialCases.get_jinx_forms()

        # Arcane Fractured Jinx forms are treated as forms of the base skin.
        elif skin_id in (222998, 222999):
            return ChromaSpecialCases.get_jinx_forms()

        # Special case: Viego (skin ID 234043) has Forms instead of chromas
        elif skin_id == 234043:
            return ChromaSpecialCases.get_viego_forms()
        
        # Special case: Viego forms (IDs 234994-234999) are treated as forms of base skin
        elif skin_id in (234994, 234995, 234996, 234997, 234998, 234999):
            return ChromaSpecialCases.get_viego_forms()
        
        # Special case: Gun Goddess Miss Fortune (skin ID 21016) has Forms instead of chromas
        elif skin_id == 21016:
            return ChromaSpecialCases.get_missfortune_forms()
        
        # Special case: Gun Goddess Miss Fortune forms (IDs 21997-21999) are treated as forms of base skin
        elif skin_id in (21997, 21998, 21999):
            return ChromaSpecialCases.get_missfortune_forms()
        
        # Special case: Risen Legend Kai'Sa (skin ID 145070) has HOL chroma instead of regular chromas
        elif skin_id == 145070:
            return ChromaSpecialCases.get_hol_chromas()
        
        # Special case: Immortalized Legend Kai'Sa (skin ID 145071) is treated as a chroma of Risen Legend
        elif skin_id == 145071:
            return ChromaSpecialCases.get_hol_chromas()
        
        # Special case: Risen Legend Ahri (skin ID 103085) has HOL chroma instead of regular chromas
        elif skin_id == 103085:
            return ChromaSpecialCases.get_ahri_hol_chromas()
        
        # Special case: Immortalized Legend Ahri (skin ID 103086) is treated as a chroma of Risen Legend Ahri
        elif skin_id == 103086:
            return ChromaSpecialCases.get_ahri_hol_chromas()
        
        # Special case: Form 2 Ahri (skin ID 103087) is treated as a chroma of Risen Legend Ahri
        elif skin_id == 103087:
            return ChromaSpecialCases.get_ahri_hol_chromas()
        
        return None
    
    @staticmethod
    def get_base_skin_id_for_special(chroma_id: int) -> Optional[int]:
        """Get base skin ID for special chromas
        
        Returns:
            Base skin ID or None if not a special chroma
        """
        try:
            chroma_id = int(chroma_id)
        except (TypeError, ValueError):
            return None

        if ChromaSpecialCases.is_elementalist_form(chroma_id):
            return 99007  # Elementalist Lux base skin ID
        
        if ChromaSpecialCases.is_mordekaiser_form(chroma_id):
            return 82054  # Sahn Uzal Mordekaiser base skin ID
        
        if ChromaSpecialCases.is_morgana_form(chroma_id):
            return 25080  # Spirit Blossom Morgana base skin ID
        
        if ChromaSpecialCases.is_sett_form(chroma_id):
            return 875066  # Radiant Sett base skin ID
        
        if ChromaSpecialCases.is_seraphine_form(chroma_id):
            return 147001  # KDA Seraphine base skin ID
        
        if chroma_id == 222060 or ChromaSpecialCases.is_jinx_form(chroma_id):
            return 222060  # Arcane Fractured Jinx base skin ID

        if chroma_id == 234043 or ChromaSpecialCases.is_viego_form(chroma_id):
            return 234043  # Revenant Reign Viego base skin ID
        
        if ChromaSpecialCases.is_missfortune_form(chroma_id):
            return 21016  # Gun Goddess Miss Fortune base skin ID
        
        if chroma_id == 21016:
            return 21016  # Gun Goddess Miss Fortune base skin ID
        
        if chroma_id == 145071:
            return 145070  # Risen Legend Kai'Sa base skin ID
        
        if chroma_id == 103086:
            return 103085  # Risen Legend Ahri base skin ID
        
        if chroma_id == 103087:
            return 103085  # Risen Legend Ahri base skin ID
        
        return None


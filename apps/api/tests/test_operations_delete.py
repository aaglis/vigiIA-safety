import unittest

from vigia_api.domain.operations import EntityStatus, OperationInUse, ZoneType
from vigia_api.services.operations import InMemoryOperationsRepository


class DeleteProtegeHistoricoTest(unittest.TestCase):
    """Excluir cadastro com histórico apagaria a rastreabilidade: o incidente guarda
    `camera_id`/`zone_id` como texto (sem FK), então a auditoria passaria a apontar para
    o nada. Nesses casos a exclusão é barrada e o caminho é desativar."""

    def setUp(self):
        self.repo = InMemoryOperationsRepository()
        self.site = self.repo.create_site("org-1", "Planta", site_id="site-1")
        self.camera = self.repo.create_camera("org-1", "site-1", name="Cam 1", stream_identifier="rtsp://x/1", camera_id="cam-1")
        self.zone = self.repo.create_zone("org-1", "site-1", "cam-1", ZoneType.RESTRICTED, {}, zone_id="zone-1", name="Porta")
        self.com_historico: set[tuple[str, str]] = set()
        self.repo._incident_lookup = lambda kind, value: (kind, value) in self.com_historico

    def test_zona_sem_historico_e_excluida(self):
        self.repo.delete_zone("org-1", "zone-1")
        self.assertEqual(self.repo.list_zones("org-1"), [])

    def test_zona_com_incidente_nao_e_excluida(self):
        self.com_historico.add(("zone", "zone-1"))
        with self.assertRaises(OperationInUse):
            self.repo.delete_zone("org-1", "zone-1")
        self.assertEqual(len(self.repo.list_zones("org-1")), 1, "zona com histórico sumiu")

    def test_camera_com_incidente_nao_e_excluida(self):
        self.com_historico.add(("camera", "cam-1"))
        with self.assertRaises(OperationInUse):
            self.repo.delete_camera("org-1", "cam-1")
        self.assertEqual(len(self.repo.list_cameras("org-1")), 1)

    def test_excluir_camera_leva_as_zonas_dela(self):
        # Espelha o ondelete=CASCADE de `zones.camera_id` no banco.
        self.repo.delete_camera("org-1", "cam-1")
        self.assertEqual(self.repo.list_cameras("org-1"), [])
        self.assertEqual(self.repo.list_zones("org-1"), [], "zona órfã de câmera")

    def test_unidade_com_camera_nao_e_excluida(self):
        with self.assertRaises(OperationInUse):
            self.repo.delete_site("org-1", "site-1")
        self.assertEqual(len(self.repo.list_sites("org-1")), 1)

    def test_unidade_vazia_e_excluida(self):
        self.repo.delete_camera("org-1", "cam-1")
        self.repo.delete_site("org-1", "site-1")
        self.assertEqual(self.repo.list_sites("org-1"), [])

    def test_nao_exclui_de_outra_organizacao(self):
        with self.assertRaises(KeyError):
            self.repo.delete_zone("org-outra", "zone-1")
        self.assertEqual(len(self.repo.list_zones("org-1")), 1)

    def test_zona_inexistente(self):
        with self.assertRaises(KeyError):
            self.repo.delete_zone("org-1", "zone-404")


class InterfaceRepositorioTest(unittest.TestCase):
    """As duas implementações precisam expor a mesma interface — foi a divergência entre
    elas que já produziu bugs que passavam verdes nos testes e quebravam no Postgres."""

    def test_sql_e_memoria_expoem_os_mesmos_deletes(self):
        from vigia_api.persistence.operations_repository import SqlAlchemyOperationsRepository

        for metodo in ("delete_zone", "delete_camera", "delete_site"):
            self.assertTrue(hasattr(InMemoryOperationsRepository, metodo), f"memória sem {metodo}")
            self.assertTrue(hasattr(SqlAlchemyOperationsRepository, metodo), f"SQL sem {metodo}")


if __name__ == "__main__":
    unittest.main()

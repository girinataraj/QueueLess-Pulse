CREATE OR REPLACE FUNCTION validate_assignment_tenant() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE member_business integer; service_business integer;
BEGIN
SELECT business_id INTO member_business FROM memberships WHERE id=NEW.membership_id;
SELECT b.business_id INTO service_business FROM services s JOIN branches b ON b.id=s.branch_id WHERE s.id=NEW.service_id;
IF member_business IS DISTINCT FROM service_business OR member_business IS NULL THEN
RAISE EXCEPTION 'Assignment must remain in membership business' USING ERRCODE='23503';
END IF;
RETURN NEW;
END;
$$;
CREATE TRIGGER assignment_tenant_guard BEFORE INSERT OR UPDATE ON service_assignments FOR EACH ROW EXECUTE FUNCTION validate_assignment_tenant();

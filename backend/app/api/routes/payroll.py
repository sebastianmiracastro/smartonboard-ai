from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import (
    User, PayrollConcept, PayrollPeriod, Payslip, PayslipItem, Department, Role,
    PayrollNovelty,
)
from app.schemas.schemas import (
    PayrollConceptCreate, PayrollConceptUpdate, PayrollConceptOut,
    PayrollPeriodCreate, PayrollPeriodOut, PayrollPeriodDetailOut, PayslipOut,
    PayrollNoveltyCreate, PayrollNoveltyOut, SettlementCreate,
)
from app.core.dependencies import require_rrhh

router = APIRouter(prefix="/api/payroll", tags=["Nómina"])

# ─── CONCEPTOS ───────────────────────────────────────────────────────────────

@router.get("/concepts", response_model=List[PayrollConceptOut])
def list_concepts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    return db.query(PayrollConcept).filter(
        PayrollConcept.company_id == current_user.company_id
    ).order_by(PayrollConcept.created_at).all()

@router.post("/concepts", response_model=PayrollConceptOut, status_code=status.HTTP_201_CREATED)
def create_concept(
    data: PayrollConceptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    if data.type not in ("devengado", "deduccion", "aporte_patronal", "provision"):
        raise HTTPException(status_code=400, detail="Tipo de concepto inválido")
    if data.calc_type not in ("fijo", "porcentaje"):
        raise HTTPException(status_code=400, detail="Tipo de cálculo inválido")

    concept = PayrollConcept(
        company_id=current_user.company_id,
        name=data.name,
        type=data.type,
        calc_type=data.calc_type,
        value=data.value,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept

@router.patch("/concepts/{concept_id}", response_model=PayrollConceptOut)
def update_concept(
    concept_id: str,
    data: PayrollConceptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    concept = db.query(PayrollConcept).filter(
        PayrollConcept.id == concept_id,
        PayrollConcept.company_id == current_user.company_id
    ).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(concept, field, value)
    db.commit()
    db.refresh(concept)
    return concept

@router.delete("/concepts/{concept_id}")
def delete_concept(
    concept_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    concept = db.query(PayrollConcept).filter(
        PayrollConcept.id == concept_id,
        PayrollConcept.company_id == current_user.company_id
    ).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    db.delete(concept)
    db.commit()
    return {"ok": True}

# ─── LIQUIDACIÓN DE PERÍODOS ─────────────────────────────────────────────────

from datetime import date

def _factor_and_days(period_start, period_end):
    """Proporción a pagar según las fechas seleccionadas (mes = 30 días).
    1 día → 1/30, mes completo (30 días) → 1.0. Si no hay fechas, mes completo."""
    if not period_start or not period_end:
        return 1.0, 30
    try:
        d1 = date.fromisoformat(period_start)
        d2 = date.fromisoformat(period_end)
    except ValueError:
        return 1.0, 30
    days = (d2 - d1).days + 1  # inclusivo
    if days <= 0:
        days = 1
    return round(days / 30.0, 4), days

def _calc_amount(concept: PayrollConcept, base: float, factor: float) -> float:
    """Monto de un concepto para el período. Los % se calculan sobre el salario
    ya prorrateado; los fijos se prorratean por el factor de días."""
    if concept.calc_type == "porcentaje":
        return round(base * (concept.value or 0) / 100, 2)
    return round((concept.value or 0) * factor, 2)

def _liquidate_employee(db, period, emp, concepts, factor, novelties):
    """Genera el comprobante de un empleado: salario prorrateado + conceptos +
    novedades. Marca novedades como aplicadas. Devuelve (dev, ded, apo, net)."""
    base = round((emp.base_salary or 0) * factor, 2)
    payslip = Payslip(
        period_id=period.id, user_id=emp.id,
        employee_name=emp.full_name,
        employee_document=emp.document_id,
        employee_role=emp.role_name,
        period_name=period.name,
        period_start=period.period_start,
        period_end=period.period_end,
        days=period.days,
        kind=period.kind,
        monthly_salary=emp.base_salary or 0,
        base_salary=base,
    )
    db.add(payslip)
    db.flush()

    db.add(PayslipItem(
        payslip_id=payslip.id, concept_id=None,
        concept_name="Salario base", type="devengado", amount=base
    ))
    total_dev, total_ded, total_apo = base, 0.0, 0.0

    for c in concepts:
        amount = _calc_amount(c, base, factor)
        db.add(PayslipItem(
            payslip_id=payslip.id, concept_id=c.id,
            concept_name=c.name, type=c.type, amount=amount
        ))
        if c.type == "devengado":
            total_dev += amount
        elif c.type == "deduccion":
            total_ded += amount
        else:
            total_apo += amount

    # Novedades individuales (monto completo, no se prorratean)
    for n in novelties:
        amount = round(n.amount or 0, 2)
        item_type = "deduccion" if n.type == "deduccion" else "devengado"
        label = n.concept_name + (" (retiro)" if n.type == "retiro" else " (novedad)")
        db.add(PayslipItem(
            payslip_id=payslip.id, concept_id=None,
            concept_name=label, type=item_type, amount=amount
        ))
        if item_type == "deduccion":
            total_ded += amount
        else:
            total_dev += amount
        n.applied = True
        n.period_id = period.id
        if n.type == "retiro":
            emp.status = "inactivo"
            emp.is_active = False

    net = round(total_dev - total_ded, 2)
    payslip.total_devengado = round(total_dev, 2)
    payslip.total_deduccion = round(total_ded, 2)
    payslip.total_aportes = round(total_apo, 2)
    payslip.net_pay = net
    return total_dev, total_ded, total_apo, net

@router.get("/periods", response_model=List[PayrollPeriodOut])
def list_periods(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    return db.query(PayrollPeriod).filter(
        PayrollPeriod.company_id == current_user.company_id
    ).order_by(PayrollPeriod.created_at.desc()).all()

@router.post("/periods", response_model=PayrollPeriodDetailOut, status_code=status.HTTP_201_CREATED)
def create_period(
    data: PayrollPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Crea un período y liquida la nómina de todos los empleados activos.

    El monto se prorratea según las fechas seleccionadas (mes = 30 días) y se
    aplican las novedades individuales pendientes de cada colaborador.
    """
    factor, days = _factor_and_days(data.period_start, data.period_end)
    month_key = data.month_key or (data.period_start[:7] if data.period_start else None)

    concepts = db.query(PayrollConcept).filter(
        PayrollConcept.company_id == current_user.company_id,
        PayrollConcept.is_active == True
    ).all()

    employees = db.query(User).filter(
        User.company_id == current_user.company_id,
        User.is_active == True,
        User.base_salary > 0
    ).all()

    if not employees:
        raise HTTPException(
            status_code=400,
            detail="No hay empleados con salario asignado para liquidar."
        )

    pending = db.query(PayrollNovelty).filter(
        PayrollNovelty.company_id == current_user.company_id,
        PayrollNovelty.applied == False
    ).all()
    novelties_by_user: dict = {}
    for n in pending:
        novelties_by_user.setdefault(n.user_id, []).append(n)

    period = PayrollPeriod(
        company_id=current_user.company_id,
        name=data.name,
        period_start=data.period_start,
        period_end=data.period_end,
        kind="nomina",
        factor=factor,
        days=days,
        month_key=month_key,
        status="procesada",
    )
    db.add(period)
    db.flush()

    grand_dev = grand_ded = grand_apo = grand_net = 0.0
    for emp in employees:
        dev, ded, apo, net = _liquidate_employee(
            db, period, emp, concepts, factor, novelties_by_user.get(emp.id, [])
        )
        grand_dev += dev; grand_ded += ded; grand_apo += apo; grand_net += net

    period.total_devengado = round(grand_dev, 2)
    period.total_deduccion = round(grand_ded, 2)
    period.total_aportes = round(grand_apo, 2)
    period.total_neto = round(grand_net, 2)
    period.employee_count = len(employees)

    db.commit()
    db.refresh(period)
    return period

@router.post("/settlement", response_model=PayrollPeriodDetailOut, status_code=status.HTTP_201_CREATED)
def create_settlement(
    data: SettlementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Liquidación por terminación de UN solo colaborador. Prorratea según las
    fechas, aplica sus novedades pendientes e inactiva al empleado."""
    emp = db.query(User).filter(
        User.id == data.user_id,
        User.company_id == current_user.company_id
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if not emp.base_salary or emp.base_salary <= 0:
        raise HTTPException(status_code=400, detail="El empleado no tiene salario asignado.")

    factor, days = _factor_and_days(data.period_start, data.period_end)
    month_key = data.month_key or (data.period_start[:7] if data.period_start else None)

    concepts = db.query(PayrollConcept).filter(
        PayrollConcept.company_id == current_user.company_id,
        PayrollConcept.is_active == True
    ).all()
    novelties = db.query(PayrollNovelty).filter(
        PayrollNovelty.company_id == current_user.company_id,
        PayrollNovelty.user_id == emp.id,
        PayrollNovelty.applied == False
    ).all()

    period = PayrollPeriod(
        company_id=current_user.company_id,
        name=data.name or f"Liquidación de retiro — {emp.full_name}",
        period_start=data.period_start,
        period_end=data.period_end,
        kind="terminacion",
        factor=factor,
        days=days,
        month_key=month_key,
        status="procesada",
        employee_count=1,
    )
    db.add(period)
    db.flush()

    dev, ded, apo, net = _liquidate_employee(db, period, emp, concepts, factor, novelties)

    # La terminación SIEMPRE inactiva al colaborador
    emp.status = "inactivo"
    emp.is_active = False

    period.total_devengado = round(dev, 2)
    period.total_deduccion = round(ded, 2)
    period.total_aportes = round(apo, 2)
    period.total_neto = round(net, 2)

    db.commit()
    db.refresh(period)
    return period

@router.get("/periods/{period_id}", response_model=PayrollPeriodDetailOut)
def get_period(
    period_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    period = db.query(PayrollPeriod).filter(
        PayrollPeriod.id == period_id,
        PayrollPeriod.company_id == current_user.company_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    return period

@router.patch("/periods/{period_id}/pay", response_model=PayrollPeriodOut)
def mark_period_paid(
    period_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    period = db.query(PayrollPeriod).filter(
        PayrollPeriod.id == period_id,
        PayrollPeriod.company_id == current_user.company_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    period.status = "pagada"
    db.commit()
    db.refresh(period)
    return period

@router.delete("/periods/{period_id}")
def delete_period(
    period_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    period = db.query(PayrollPeriod).filter(
        PayrollPeriod.id == period_id,
        PayrollPeriod.company_id == current_user.company_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    db.delete(period)  # cascade borra payslips e items
    db.commit()
    return {"ok": True}

@router.get("/payslips/{payslip_id}", response_model=PayslipOut)
def get_payslip(
    payslip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    payslip = (
        db.query(Payslip)
        .join(PayrollPeriod, Payslip.period_id == PayrollPeriod.id)
        .filter(
            Payslip.id == payslip_id,
            PayrollPeriod.company_id == current_user.company_id
        )
        .first()
    )
    if not payslip:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return payslip

@router.get("/employees/{user_id}/payslips", response_model=List[PayslipOut])
def employee_payslips(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Historial de comprobantes individuales de un colaborador (todas sus nóminas)."""
    emp = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return (
        db.query(Payslip)
        .join(PayrollPeriod, Payslip.period_id == PayrollPeriod.id)
        .filter(
            Payslip.user_id == user_id,
            PayrollPeriod.company_id == current_user.company_id
        )
        .order_by(Payslip.created_at.desc())
        .all()
    )

# ─── NOVEDADES INDIVIDUALES ──────────────────────────────────────────────────

@router.get("/novelties", response_model=List[PayrollNoveltyOut])
def list_novelties(
    only_pending: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    q = db.query(PayrollNovelty).filter(
        PayrollNovelty.company_id == current_user.company_id
    )
    if only_pending:
        q = q.filter(PayrollNovelty.applied == False)
    return q.order_by(PayrollNovelty.created_at.desc()).all()

@router.post("/novelties", response_model=PayrollNoveltyOut, status_code=status.HTTP_201_CREATED)
def create_novelty(
    data: PayrollNoveltyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    if data.type not in ("devengado", "deduccion", "retiro"):
        raise HTTPException(status_code=400, detail="Tipo de novedad inválido")
    emp = db.query(User).filter(
        User.id == data.user_id,
        User.company_id == current_user.company_id
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    novelty = PayrollNovelty(
        company_id=current_user.company_id,
        user_id=emp.id,
        employee_name=emp.full_name,
        concept_name=data.concept_name,
        type=data.type,
        amount=data.amount,
        description=data.description,
    )
    db.add(novelty)
    db.commit()
    db.refresh(novelty)
    return novelty

@router.delete("/novelties/{novelty_id}")
def delete_novelty(
    novelty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    novelty = db.query(PayrollNovelty).filter(
        PayrollNovelty.id == novelty_id,
        PayrollNovelty.company_id == current_user.company_id
    ).first()
    if not novelty:
        raise HTTPException(status_code=404, detail="Novedad no encontrada")
    if novelty.applied:
        raise HTTPException(status_code=400, detail="No se puede eliminar una novedad ya aplicada")
    db.delete(novelty)
    db.commit()
    return {"ok": True}

# ─── RESUMEN MENSUAL (agrupa quincenas en el total del mes) ───────────────────

@router.get("/monthly-summary")
def monthly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    periods = db.query(PayrollPeriod).filter(
        PayrollPeriod.company_id == current_user.company_id
    ).all()

    months: dict = {}
    for p in periods:
        key = p.month_key or (p.period_start[:7] if p.period_start else "sin_fecha")
        m = months.setdefault(key, {
            "month": key, "total_neto": 0.0, "total_devengado": 0.0,
            "total_deduccion": 0.0, "total_aportes": 0.0, "periods": 0,
        })
        m["total_neto"] += p.total_neto or 0
        m["total_devengado"] += p.total_devengado or 0
        m["total_deduccion"] += p.total_deduccion or 0
        m["total_aportes"] += p.total_aportes or 0
        m["periods"] += 1

    result = sorted(months.values(), key=lambda x: x["month"], reverse=True)
    for m in result:
        for k in ("total_neto", "total_devengado", "total_deduccion", "total_aportes"):
            m[k] = round(m[k], 2)
    return result

# ─── MÉTRICAS DE RR.HH. ──────────────────────────────────────────────────────

@router.get("/metrics")
def hr_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    users = db.query(User).filter(
        User.company_id == current_user.company_id,
        User.is_active == True
    ).all()

    depts = {d.id: d.name for d in db.query(Department).filter(
        Department.company_id == current_user.company_id
    ).all()}

    headcount = len(users)
    by_status = {}
    by_gender = {}
    by_contract = {}
    by_department = {}
    salaries = []
    total_children = 0

    for u in users:
        by_status[u.status or "—"] = by_status.get(u.status or "—", 0) + 1
        by_gender[u.gender or "no_definido"] = by_gender.get(u.gender or "no_definido", 0) + 1
        by_contract[u.contract_type or "no_definido"] = by_contract.get(u.contract_type or "no_definido", 0) + 1
        dept_name = depts.get(u.department_id, "Sin departamento")
        by_department[dept_name] = by_department.get(dept_name, 0) + 1
        if u.base_salary:
            salaries.append(u.base_salary)
        total_children += (u.num_children or 0)

    total_payroll = round(sum(salaries), 2)
    avg_salary = round(total_payroll / len(salaries), 2) if salaries else 0

    return {
        "headcount": headcount,
        "total_payroll": total_payroll,
        "avg_salary": avg_salary,
        "total_children": total_children,
        "onboarding_count": by_status.get("onboarding", 0),
        "active_count": by_status.get("activo", 0),
        "by_status": by_status,
        "by_gender": by_gender,
        "by_contract": by_contract,
        "by_department": by_department,
    }
